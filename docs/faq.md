# Frequently Asked Questions (FAQ)

## General Questions

### What is MAMS?

MAMS (Media Asset Management System) is an enterprise-grade, microservices-based platform for managing digital media assets. It provides comprehensive features for storing, organizing, searching, and distributing media content including videos, images, audio files, and documents.

### Who is MAMS designed for?

MAMS is designed for:
- **Broadcast companies** - Managing vast libraries of video content
- **Production houses** - Organizing project assets and deliverables
- **News organizations** - Quick access to archival footage and current content
- **Marketing teams** - Central repository for brand assets
- **Educational institutions** - Managing educational content libraries
- **Content creators** - Professional asset management for creators

### What file types does MAMS support?

MAMS supports a wide range of media formats:
- **Video**: MP4, MOV, AVI, MKV, ProRes, DNxHD, MXF, and more
- **Audio**: MP3, WAV, FLAC, AAC, AIFF, and more
- **Images**: JPEG, PNG, TIFF, RAW, PSD, AI, and more
- **Documents**: PDF, DOC/DOCX, XLS/XLSX, PPT/PPTX
- **Other**: 3D files, subtitles, project files

### Is MAMS cloud-based or on-premises?

MAMS can be deployed in multiple ways:
- **On-premises** - Full control over your infrastructure
- **Private cloud** - Your own cloud infrastructure
- **Public cloud** - AWS, Azure, Google Cloud
- **Hybrid** - Combination of on-premises and cloud

## Installation & Setup

### What are the system requirements?

**Minimum Requirements:**
- CPU: 8 cores
- RAM: 32GB
- Storage: 500GB SSD
- OS: Ubuntu 20.04+, CentOS 8+, or macOS 12+

**Recommended Production:**
- CPU: 16+ cores
- RAM: 64GB+
- Storage: 2TB+ NVMe SSD
- Network: 10Gbps connection

### How long does installation take?

- **Docker Compose setup**: 15-30 minutes
- **Kubernetes deployment**: 1-2 hours
- **Full production setup**: 4-8 hours (including configuration and testing)

### Can I try MAMS before purchasing?

Yes! We offer:
- **Free trial**: 30-day full-featured trial
- **Demo environment**: Online demo with sample data
- **Community edition**: Limited features for small teams

### Do you provide installation support?

Yes, we offer several support options:
- **Documentation**: Comprehensive installation guides
- **Community support**: Forums and Discord channel
- **Professional services**: Paid installation and configuration
- **Training**: On-site or remote training sessions

## Features & Functionality

### Can MAMS integrate with our existing systems?

Yes, MAMS provides extensive integration capabilities:
- **REST API**: Full API coverage for all features
- **Webhooks**: Real-time event notifications
- **Export formats**: AAF, XML, EDL, OTIO
- **Storage systems**: S3, Azure Blob, Google Cloud Storage
- **NLE integration**: Premiere Pro, Final Cut Pro, DaVinci Resolve
- **SSO providers**: LDAP, SAML, OAuth2

### Does MAMS support AI/ML features?

Yes, MAMS includes AI-powered features:
- **Auto-tagging**: Automatic content tagging
- **Transcription**: Speech-to-text for videos
- **Face recognition**: Identify people in videos/images
- **Scene detection**: Automatic scene segmentation
- **Content moderation**: Detect inappropriate content
- **Recommendations**: Suggest related assets

### How does search work in MAMS?

MAMS provides multiple search capabilities:
- **Full-text search**: Search across all metadata
- **Advanced filters**: By type, date, size, creator, etc.
- **Natural language**: "Find all videos from last month"
- **Visual search**: Find similar images
- **Facial search**: Find assets containing specific people
- **Audio search**: Search within transcriptions

### Can I customize metadata fields?

Yes, MAMS offers flexible metadata management:
- **Custom fields**: Create any field type
- **Field validation**: Ensure data quality
- **Controlled vocabularies**: Dropdown lists
- **Inherited metadata**: From folders/projects
- **Bulk editing**: Update multiple assets at once

## Security & Compliance

### Is MAMS secure?

MAMS implements enterprise-grade security:
- **Encryption**: At rest and in transit
- **Authentication**: MFA, SSO, API keys
- **Authorization**: Role-based access control
- **Audit logs**: Complete activity tracking
- **Compliance**: GDPR, HIPAA ready
- **Penetration tested**: Regular security audits

### How are permissions managed?

MAMS uses a flexible permission system:
- **Role-based**: Admin, Editor, Viewer, custom roles
- **Project-based**: Permissions per project
- **Asset-level**: Fine-grained permissions
- **Inheritance**: From parent folders/projects
- **Time-based**: Temporary access grants

### Can I comply with GDPR/data regulations?

Yes, MAMS includes compliance features:
- **Right to deletion**: Remove user data
- **Data export**: Export all user data
- **Consent tracking**: Record user consent
- **Data minimization**: Store only necessary data
- **Audit trails**: Track all data access

### How is backup handled?

MAMS provides comprehensive backup options:
- **Automated backups**: Scheduled database and file backups
- **Point-in-time recovery**: Restore to any point
- **Geo-redundancy**: Backups in multiple locations
- **Disaster recovery**: Full DR procedures
- **Backup testing**: Automated restore testing

## Performance & Scalability

### How many assets can MAMS handle?

MAMS is designed for scale:
- **Assets**: Millions of assets
- **Users**: Thousands of concurrent users
- **Storage**: Petabytes of data
- **Throughput**: Hundreds of uploads/second

### What about performance optimization?

MAMS includes many optimizations:
- **CDN integration**: Fast global delivery
- **Caching**: Multi-layer caching
- **Load balancing**: Distribute traffic
- **Database optimization**: Query optimization
- **Async processing**: Background jobs

### Can MAMS scale with our growth?

Yes, MAMS is built to scale:
- **Horizontal scaling**: Add more servers
- **Microservices**: Scale individual components
- **Cloud-native**: Auto-scaling support
- **Storage tiering**: Hot/warm/cold storage

## Pricing & Licensing

### What are the licensing options?

MAMS offers flexible licensing:
- **Perpetual license**: One-time purchase
- **Subscription**: Annual or monthly
- **User-based**: Price per user
- **Usage-based**: Price per TB stored
- **Enterprise**: Custom pricing

### Is there a free version?

Yes, we offer:
- **Community Edition**: Up to 5 users, 1TB storage
- **Educational**: Free for qualified institutions
- **Non-profit**: Discounted pricing
- **Open source**: Core components on GitHub

### What's included in support?

Support packages include:
- **Basic**: Email support, documentation
- **Standard**: + Phone support, 24-hour response
- **Premium**: + 24/7 support, 1-hour response
- **Enterprise**: + Dedicated support team

## Technical Questions

### What technology stack does MAMS use?

**Backend:**
- Language: Python 3.11+
- Framework: FastAPI
- Databases: PostgreSQL, MongoDB, OpenSearch
- Cache: Redis
- Message Queue: RabbitMQ

**Frontend:**
- Framework: React 18
- Language: TypeScript
- State: Redux Toolkit
- UI: Material-UI

### Can I develop custom plugins?

Yes, MAMS supports extensions:
- **Plugin API**: Well-documented API
- **SDK**: Python and JavaScript SDKs
- **Webhooks**: React to events
- **Custom workflows**: Build your own
- **UI extensions**: Add custom panels

### How do updates work?

MAMS updates are straightforward:
- **Notifications**: In-app update notifications
- **Changelogs**: Detailed release notes
- **Backward compatibility**: API versioning
- **Zero-downtime**: Rolling updates
- **Rollback**: Easy rollback procedure

### Can I contribute to MAMS?

Yes! We welcome contributions:
- **GitHub**: Submit issues and PRs
- **Documentation**: Help improve docs
- **Translations**: Add new languages
- **Plugins**: Share your plugins
- **Community**: Help other users

## Troubleshooting

### Why is upload failing?

Common causes and solutions:
1. **File too large**: Check upload limits in settings
2. **Network timeout**: Use chunked upload for large files
3. **Permission denied**: Verify user has upload permission
4. **Storage full**: Check available storage space
5. **Format not supported**: Check supported formats list

### Why is search not returning results?

Troubleshooting steps:
1. **Indexing delay**: Wait for assets to be indexed
2. **Permission filters**: Check if you have access
3. **Search syntax**: Verify query format
4. **Index corruption**: Rebuild search index
5. **Service down**: Check OpenSearch status

### How do I improve performance?

Performance optimization tips:
1. **Enable caching**: Configure Redis caching
2. **Use CDN**: Enable CDN for media delivery
3. **Optimize queries**: Add database indexes
4. **Scale services**: Add more instances
5. **Storage tiering**: Move old assets to cold storage

### Why can't users log in?

Common authentication issues:
1. **Wrong credentials**: Reset password
2. **Account locked**: Check lockout policy
3. **SSO misconfigured**: Verify SSO settings
4. **MFA issues**: Sync time on devices
5. **Session expired**: Clear cookies and retry

## Migration & Integration

### Can I migrate from another DAM system?

Yes, we support migration from:
- **Adobe Experience Manager**
- **Bynder**
- **Canto**
- **Widen**
- **Custom systems**: Via API or database

Migration tools provided:
- **Data mapping**: Map metadata fields
- **Bulk import**: Import assets and metadata
- **Validation**: Verify migrated data
- **Incremental sync**: Keep systems in sync

### How do I integrate with Adobe Creative Cloud?

MAMS provides Adobe integrations:
1. **Panel extension**: Access MAMS from Creative apps
2. **Direct import**: Import assets into projects
3. **Auto-sync**: Sync changes back to MAMS
4. **Metadata mapping**: Preserve metadata
5. **Proxy workflows**: Work with proxies

### Can MAMS work with our CDN?

Yes, MAMS supports CDN integration:
- **Built-in support**: AWS CloudFront, Cloudflare
- **Custom CDN**: API for any CDN
- **Origin pull**: CDN pulls from MAMS
- **Push to CDN**: Proactive distribution
- **Cache invalidation**: Update content

## Best Practices

### How should I organize assets?

Recommended organization:
1. **Project-based**: Group by project
2. **Date-based**: Year/Month folders
3. **Type-based**: Separate by media type
4. **Metadata-driven**: Rely on search
5. **Hybrid approach**: Combine methods

### What metadata should I track?

Essential metadata fields:
- **Title**: Descriptive name
- **Description**: Detailed information
- **Tags**: Searchable keywords
- **Creator**: Who created it
- **Rights**: Usage rights
- **Project**: Associated project
- **Date**: Creation/modification date
- **Technical**: Format, resolution, duration

### How often should I backup?

Backup recommendations:
- **Database**: Daily incremental, weekly full
- **Files**: Continuous to cloud storage
- **Configuration**: After each change
- **Test restores**: Monthly
- **Offsite**: Always maintain offsite backup

### What are the security best practices?

Security recommendations:
1. **Enable MFA**: For all users
2. **Regular audits**: Review permissions
3. **Strong passwords**: Enforce policy
4. **API key rotation**: Rotate regularly
5. **Update regularly**: Apply security patches
6. **Monitor logs**: Watch for anomalies
7. **Limit access**: Principle of least privilege

---

## Still Have Questions?

If your question isn't answered here:

1. **Check Documentation**: Detailed guides for all features
2. **Community Forum**: Ask the community
3. **Support Ticket**: Contact our support team
4. **Discord Channel**: Real-time help
5. **GitHub Issues**: Report bugs or request features

**Contact Information:**
- Email: support@mams.example.com
- Forum: community.mams.example.com
- Discord: discord.gg/mams
- Documentation: docs.mams.example.com