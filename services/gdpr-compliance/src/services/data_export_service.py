"""Data Export Service for GDPR compliance"""

import json
import csv
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import pandas as pd
from io import StringIO, BytesIO
import zipfile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
import aiofiles
import logging

from ..core.config import settings
from ..db.models import DataRequest, DataRequestStatus, DataMapping, DataCategory
from ..models.schemas import ExportFormat, DataExportRequest
from ..utils.anonymization import anonymize_data
from ..utils.encryption import encrypt_file
from .audit_service import AuditService


class DataExportService:
    """Service for handling GDPR data export requests"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.logger = logging.getLogger(__name__)
        self.audit_service = AuditService(db)
        self.export_path = Path(settings.export_storage_path)
        self.export_path.mkdir(exist_ok=True)
    
    async def export_user_data(
        self,
        user_id: str,
        export_format: ExportFormat,
        categories: Optional[List[str]] = None,
        anonymize: bool = False,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Export all user data in requested format"""
        try:
            # Get data mappings for included categories
            mappings = await self._get_data_mappings(categories)
            
            # Collect data from all mapped tables
            all_data = {}
            total_records = 0
            
            for mapping in mappings:
                table_data = await self._extract_table_data(
                    user_id=user_id,
                    mapping=mapping,
                    date_from=date_from,
                    date_to=date_to
                )
                
                if table_data:
                    # Apply anonymization if requested
                    if anonymize and mapping.anonymization_method:
                        table_data = await self._anonymize_data(
                            data=table_data,
                            method=mapping.anonymization_method,
                            params=mapping.anonymization_params
                        )
                    
                    table_name = mapping.table_name
                    if table_name not in all_data:
                        all_data[table_name] = []
                    
                    all_data[table_name].extend(table_data)
                    total_records += len(table_data)
            
            # Generate export file
            export_file = await self._generate_export_file(
                data=all_data,
                user_id=user_id,
                format=export_format
            )
            
            # Log audit event
            await self.audit_service.log_data_export(
                user_id=user_id,
                categories=[m.category.category_name for m in mappings if m.category],
                format=export_format,
                record_count=total_records
            )
            
            return {
                "file_path": str(export_file),
                "format": export_format,
                "size_bytes": export_file.stat().st_size,
                "record_count": total_records,
                "categories_included": [m.category.category_name for m in mappings if m.category],
                "exported_at": datetime.utcnow()
            }
            
        except Exception as e:
            self.logger.error(f"Error exporting user data: {str(e)}")
            raise
    
    async def _get_data_mappings(
        self, 
        categories: Optional[List[str]] = None
    ) -> List[DataMapping]:
        """Get data mappings for specified categories"""
        query = select(DataMapping).join(DataCategory).where(
            DataMapping.include_in_export == True
        )
        
        if categories:
            query = query.where(DataCategory.category_name.in_(categories))
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def _extract_table_data(
        self,
        user_id: str,
        mapping: DataMapping,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Extract data from a specific table for a user"""
        try:
            # Build dynamic query
            query_parts = [
                f"SELECT * FROM {mapping.table_name}",
                f"WHERE user_id = :user_id"
            ]
            
            params = {"user_id": user_id}
            
            # Add date filters if provided
            if date_from:
                query_parts.append("AND created_at >= :date_from")
                params["date_from"] = date_from
            
            if date_to:
                query_parts.append("AND created_at <= :date_to")
                params["date_to"] = date_to
            
            query_str = " ".join(query_parts)
            
            # Execute query
            result = await self.db.execute(text(query_str), params)
            rows = result.fetchall()
            
            # Convert to list of dicts
            if rows:
                columns = result.keys()
                return [dict(zip(columns, row)) for row in rows]
            
            return []
            
        except Exception as e:
            self.logger.warning(f"Error extracting data from {mapping.table_name}: {str(e)}")
            return []
    
    async def _anonymize_data(
        self,
        data: List[Dict[str, Any]],
        method: str,
        params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Apply anonymization to data"""
        return [anonymize_data(record, method, params) for record in data]
    
    async def _generate_export_file(
        self,
        data: Dict[str, List[Dict[str, Any]]],
        user_id: str,
        format: ExportFormat
    ) -> Path:
        """Generate export file in requested format"""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        base_filename = f"gdpr_export_{user_id}_{timestamp}"
        
        if format == ExportFormat.JSON:
            return await self._export_json(data, base_filename)
        elif format == ExportFormat.CSV:
            return await self._export_csv(data, base_filename)
        elif format == ExportFormat.EXCEL:
            return await self._export_excel(data, base_filename)
        elif format == ExportFormat.XML:
            return await self._export_xml(data, base_filename)
        elif format == ExportFormat.PDF:
            return await self._export_pdf(data, base_filename)
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    async def _export_json(
        self,
        data: Dict[str, List[Dict[str, Any]]],
        base_filename: str
    ) -> Path:
        """Export data as JSON"""
        filename = self.export_path / f"{base_filename}.json"
        
        # Convert datetime objects to strings
        def json_serializer(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            return str(obj)
        
        async with aiofiles.open(filename, 'w') as f:
            await f.write(json.dumps(data, indent=2, default=json_serializer))
        
        return filename
    
    async def _export_csv(
        self,
        data: Dict[str, List[Dict[str, Any]]],
        base_filename: str
    ) -> Path:
        """Export data as CSV (multiple files in ZIP)"""
        zip_filename = self.export_path / f"{base_filename}.zip"
        
        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for table_name, records in data.items():
                if not records:
                    continue
                
                # Convert to CSV
                df = pd.DataFrame(records)
                csv_buffer = StringIO()
                df.to_csv(csv_buffer, index=False)
                
                # Add to ZIP
                csv_filename = f"{table_name}.csv"
                zipf.writestr(csv_filename, csv_buffer.getvalue())
        
        return zip_filename
    
    async def _export_excel(
        self,
        data: Dict[str, List[Dict[str, Any]]],
        base_filename: str
    ) -> Path:
        """Export data as Excel with multiple sheets"""
        filename = self.export_path / f"{base_filename}.xlsx"
        
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            for table_name, records in data.items():
                if not records:
                    continue
                
                df = pd.DataFrame(records)
                # Truncate sheet name to Excel's 31 character limit
                sheet_name = table_name[:31]
                df.to_excel(writer, sheet_name=sheet_name, index=False)
        
        return filename
    
    async def _export_xml(
        self,
        data: Dict[str, List[Dict[str, Any]]],
        base_filename: str
    ) -> Path:
        """Export data as XML"""
        filename = self.export_path / f"{base_filename}.xml"
        
        xml_content = ['<?xml version="1.0" encoding="UTF-8"?>']
        xml_content.append('<gdpr_export>')
        xml_content.append(f'  <export_date>{datetime.utcnow().isoformat()}</export_date>')
        xml_content.append('  <data>')
        
        for table_name, records in data.items():
            xml_content.append(f'    <table name="{table_name}">')
            for record in records:
                xml_content.append('      <record>')
                for key, value in record.items():
                    # Escape XML special characters
                    if value is not None:
                        value_str = str(value).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                        xml_content.append(f'        <{key}>{value_str}</{key}>')
                    else:
                        xml_content.append(f'        <{key}/>')
                xml_content.append('      </record>')
            xml_content.append('    </table>')
        
        xml_content.append('  </data>')
        xml_content.append('</gdpr_export>')
        
        async with aiofiles.open(filename, 'w') as f:
            await f.write('\n'.join(xml_content))
        
        return filename
    
    async def _export_pdf(
        self,
        data: Dict[str, List[Dict[str, Any]]],
        base_filename: str
    ) -> Path:
        """Export data as PDF (simplified - would use reportlab in production)"""
        # For now, convert to formatted text
        # In production, use reportlab or similar for proper PDF generation
        filename = self.export_path / f"{base_filename}.txt"
        
        content = []
        content.append("GDPR DATA EXPORT REPORT")
        content.append("=" * 50)
        content.append(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        content.append("")
        
        for table_name, records in data.items():
            content.append(f"\n{table_name.upper()}")
            content.append("-" * len(table_name))
            content.append(f"Records: {len(records)}")
            content.append("")
            
            if records:
                # Show first few records as example
                for i, record in enumerate(records[:3]):
                    content.append(f"Record {i+1}:")
                    for key, value in record.items():
                        content.append(f"  {key}: {value}")
                    content.append("")
                
                if len(records) > 3:
                    content.append(f"... and {len(records) - 3} more records")
                    content.append("")
        
        async with aiofiles.open(filename, 'w') as f:
            await f.write('\n'.join(content))
        
        return filename
    
    async def process_export_request(
        self,
        request_id: str,
        export_request: DataExportRequest
    ) -> None:
        """Process a data export request asynchronously"""
        try:
            # Update request status
            await self._update_request_status(
                request_id, 
                DataRequestStatus.IN_PROGRESS
            )
            
            # Perform export
            export_result = await self.export_user_data(
                user_id=str(export_request.user_id),
                export_format=export_request.format,
                categories=export_request.categories,
                anonymize=export_request.anonymize_data,
                date_from=export_request.date_from,
                date_to=export_request.date_to
            )
            
            # Encrypt the export file if configured
            if settings.encryption_key:
                encrypted_path = await encrypt_file(
                    Path(export_result["file_path"]),
                    settings.encryption_key
                )
                export_result["file_path"] = str(encrypted_path)
            
            # Update request with results
            await self._update_request_complete(
                request_id=request_id,
                export_path=export_result["file_path"],
                export_size=export_result["size_bytes"],
                result_data=export_result
            )
            
        except Exception as e:
            self.logger.error(f"Error processing export request: {str(e)}")
            await self._update_request_failed(request_id, str(e))
    
    async def _update_request_status(
        self,
        request_id: str,
        status: DataRequestStatus
    ) -> None:
        """Update data request status"""
        result = await self.db.execute(
            select(DataRequest).where(DataRequest.request_id == request_id)
        )
        request = result.scalar_one_or_none()
        
        if request:
            request.status = status
            request.processed_at = datetime.utcnow() if status == DataRequestStatus.IN_PROGRESS else None
            await self.db.commit()
    
    async def _update_request_complete(
        self,
        request_id: str,
        export_path: str,
        export_size: int,
        result_data: Dict[str, Any]
    ) -> None:
        """Update request as completed"""
        result = await self.db.execute(
            select(DataRequest).where(DataRequest.request_id == request_id)
        )
        request = result.scalar_one_or_none()
        
        if request:
            request.status = DataRequestStatus.COMPLETED
            request.processed_at = datetime.utcnow()
            request.export_path = export_path
            request.export_size_bytes = export_size
            request.result_data = result_data
            await self.db.commit()
    
    async def _update_request_failed(
        self,
        request_id: str,
        error_message: str
    ) -> None:
        """Update request as failed"""
        result = await self.db.execute(
            select(DataRequest).where(DataRequest.request_id == request_id)
        )
        request = result.scalar_one_or_none()
        
        if request:
            request.status = DataRequestStatus.FAILED
            request.error_message = error_message
            request.processed_at = datetime.utcnow()
            await self.db.commit()
    
    async def cleanup_old_exports(self, retention_days: int) -> int:
        """Clean up old export files"""
        cutoff_date = datetime.utcnow().timestamp() - (retention_days * 24 * 60 * 60)
        deleted_count = 0
        
        for export_file in self.export_path.iterdir():
            if export_file.is_file() and export_file.stat().st_mtime < cutoff_date:
                try:
                    export_file.unlink()
                    deleted_count += 1
                except Exception as e:
                    self.logger.error(f"Error deleting old export {export_file}: {str(e)}")
        
        return deleted_count