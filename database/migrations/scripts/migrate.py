#!/usr/bin/env python3
"""
MAMS Database Migration Management Script
Provides a CLI interface for managing database migrations across all services
"""
import os
import sys
import subprocess
import click
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
import time

# Load environment variables
load_dotenv()

console = Console()

# Database configurations
DATABASES = {
    'users': {
        'url': os.getenv('USERS_DATABASE_URL', 'postgresql://mams_app:mams_dev_password@localhost:5432/mams_users'),
        'description': 'User management, authentication, and authorization'
    },
    'assets': {
        'url': os.getenv('ASSETS_DATABASE_URL', 'postgresql://mams_app:mams_dev_password@localhost:5432/mams_assets'),
        'description': 'Asset management, projects, and collections'
    },
    'metadata': {
        'url': os.getenv('METADATA_DATABASE_URL', 'postgresql://mams_app:mams_dev_password@localhost:5432/mams_metadata'),
        'description': 'Flexible metadata schemas and vocabularies'
    },
    'workflow': {
        'url': os.getenv('WORKFLOW_DATABASE_URL', 'postgresql://mams_app:mams_dev_password@localhost:5432/mams_workflow'),
        'description': 'Workflow engine and automation'
    },
    'rights': {
        'url': os.getenv('RIGHTS_DATABASE_URL', 'postgresql://mams_app:mams_dev_password@localhost:5432/mams_rights'),
        'description': 'Rights management and licensing'
    },
    'audit': {
        'url': os.getenv('AUDIT_DATABASE_URL', 'postgresql://mams_app:mams_dev_password@localhost:5432/mams_audit'),
        'description': 'Audit logs and analytics'
    }
}

def run_alembic_command(command, database=None, *args):
    """Run an alembic command with proper environment setup"""
    env = os.environ.copy()
    
    if database:
        env['MAMS_TARGET_DB'] = database
    
    # Change to the migrations directory
    migrations_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    cmd = ['alembic'] + list(command) + list(args)
    
    try:
        result = subprocess.run(
            cmd,
            cwd=migrations_dir,
            env=env,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout, result.stderr, 0
    except subprocess.CalledProcessError as e:
        return e.stdout, e.stderr, e.returncode

def check_database_connection(database):
    """Check if database is accessible"""
    try:
        import psycopg2
        url = DATABASES[database]['url']
        # Parse URL for connection parameters
        # This is a simplified parser - in production, use proper URL parsing
        conn = psycopg2.connect(url)
        conn.close()
        return True
    except Exception as e:
        console.print(f"[red]Connection failed for {database}: {e}[/red]")
        return False

@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.pass_context
def cli(ctx, verbose):
    """MAMS Database Migration Management CLI"""
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose

@cli.command()
@click.option('--database', '-d', type=click.Choice(list(DATABASES.keys()) + ['all']), 
              default='all', help='Database to check')
def status(database):
    """Show migration status for databases"""
    databases = [database] if database != 'all' else list(DATABASES.keys())
    
    table = Table(title="Database Migration Status")
    table.add_column("Database", style="cyan", no_wrap=True)
    table.add_column("Status", style="magenta")
    table.add_column("Current Revision", style="green")
    table.add_column("Head Revision", style="yellow")
    
    for db in databases:
        console.print(f"\n[cyan]Checking {db} database...[/cyan]")
        
        if not check_database_connection(db):
            table.add_row(db, "[red]Connection Failed[/red]", "N/A", "N/A")
            continue
        
        # Get current revision
        stdout, stderr, code = run_alembic_command(['current'], db)
        if code != 0:
            table.add_row(db, "[red]Error[/red]", stderr.strip(), "N/A")
            continue
        
        current = stdout.strip() if stdout.strip() else "No migrations"
        
        # Get head revision
        stdout, stderr, code = run_alembic_command(['heads'], db)
        head = stdout.strip() if stdout.strip() else "No migrations"
        
        # Check if up to date
        if current == head and current != "No migrations":
            status_text = "[green]Up to date[/green]"
        elif current == "No migrations":
            status_text = "[yellow]Not initialized[/yellow]"
        else:
            status_text = "[red]Needs update[/red]"
        
        table.add_row(db, status_text, current, head)
    
    console.print(table)

@cli.command()
@click.option('--database', '-d', type=click.Choice(list(DATABASES.keys()) + ['all']), 
              default='all', help='Database to migrate')
@click.option('--revision', '-r', help='Target revision (default: head)')
@click.option('--sql', is_flag=True, help='Generate SQL only, don\'t execute')
def upgrade(database, revision, sql):
    """Upgrade database(s) to target revision"""
    databases = [database] if database != 'all' else list(DATABASES.keys())
    target = revision or 'head'
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        
        for db in databases:
            task = progress.add_task(f"Upgrading {db}...", total=None)
            
            if not check_database_connection(db):
                progress.remove_task(task)
                console.print(f"[red]Skipping {db} due to connection issues[/red]")
                continue
            
            # Run upgrade
            cmd = ['upgrade', target]
            if sql:
                cmd.append('--sql')
            
            stdout, stderr, code = run_alembic_command(cmd, db)
            
            progress.remove_task(task)
            
            if code == 0:
                console.print(f"[green]✓ {db} upgraded successfully[/green]")
                if sql and stdout:
                    console.print(Panel(stdout, title=f"{db} SQL", expand=False))
            else:
                console.print(f"[red]✗ {db} upgrade failed[/red]")
                if stderr:
                    console.print(Panel(stderr, title=f"{db} Error", expand=False))

@cli.command()
@click.option('--database', '-d', type=click.Choice(list(DATABASES.keys()) + ['all']), 
              default='all', help='Database to downgrade')
@click.option('--revision', '-r', required=True, help='Target revision')
@click.option('--sql', is_flag=True, help='Generate SQL only, don\'t execute')
def downgrade(database, revision, sql):
    """Downgrade database(s) to target revision"""
    databases = [database] if database != 'all' else list(DATABASES.keys())
    
    # Confirm downgrade
    if not click.confirm(f"Are you sure you want to downgrade {database} to {revision}?"):
        return
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        
        for db in databases:
            task = progress.add_task(f"Downgrading {db}...", total=None)
            
            if not check_database_connection(db):
                progress.remove_task(task)
                console.print(f"[red]Skipping {db} due to connection issues[/red]")
                continue
            
            # Run downgrade
            cmd = ['downgrade', revision]
            if sql:
                cmd.append('--sql')
            
            stdout, stderr, code = run_alembic_command(cmd, db)
            
            progress.remove_task(task)
            
            if code == 0:
                console.print(f"[green]✓ {db} downgraded successfully[/green]")
                if sql and stdout:
                    console.print(Panel(stdout, title=f"{db} SQL", expand=False))
            else:
                console.print(f"[red]✗ {db} downgrade failed[/red]")
                if stderr:
                    console.print(Panel(stderr, title=f"{db} Error", expand=False))

@cli.command()
@click.option('--database', '-d', type=click.Choice(list(DATABASES.keys())), 
              required=True, help='Database for migration')
@click.option('--message', '-m', required=True, help='Migration message')
@click.option('--autogenerate', is_flag=True, help='Auto-generate migration from model changes')
def revision(database, message, autogenerate):
    """Create a new migration revision"""
    cmd = ['revision', '-m', message]
    if autogenerate:
        cmd.append('--autogenerate')
    
    stdout, stderr, code = run_alembic_command(cmd, database)
    
    if code == 0:
        console.print(f"[green]✓ Migration created for {database}[/green]")
        if stdout:
            console.print(stdout)
    else:
        console.print(f"[red]✗ Failed to create migration for {database}[/red]")
        if stderr:
            console.print(stderr)

@cli.command()
@click.option('--database', '-d', type=click.Choice(list(DATABASES.keys()) + ['all']), 
              default='all', help='Database to show history for')
@click.option('--verbose', '-v', is_flag=True, help='Show detailed history')
def history(database, verbose):
    """Show migration history"""
    databases = [database] if database != 'all' else list(DATABASES.keys())
    
    for db in databases:
        console.print(f"\n[cyan]Migration History for {db}:[/cyan]")
        
        if not check_database_connection(db):
            console.print(f"[red]Connection failed for {db}[/red]")
            continue
        
        cmd = ['history']
        if verbose:
            cmd.append('--verbose')
        
        stdout, stderr, code = run_alembic_command(cmd, db)
        
        if code == 0:
            if stdout:
                console.print(stdout)
            else:
                console.print("[yellow]No migration history found[/yellow]")
        else:
            console.print(f"[red]Error getting history: {stderr}[/red]")

@cli.command()
def init():
    """Initialize migration environment"""
    console.print("[cyan]Initializing migration environment...[/cyan]")
    
    # Check if alembic.ini exists
    migrations_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    alembic_ini = os.path.join(migrations_dir, 'alembic.ini')
    
    if os.path.exists(alembic_ini):
        console.print("[green]✓ Migration environment already initialized[/green]")
        return
    
    # Initialize alembic
    stdout, stderr, code = run_alembic_command(['init', 'alembic'])
    
    if code == 0:
        console.print("[green]✓ Migration environment initialized[/green]")
    else:
        console.print(f"[red]✗ Failed to initialize: {stderr}[/red]")

@cli.command()
@click.option('--database', '-d', type=click.Choice(list(DATABASES.keys()) + ['all']), 
              default='all', help='Database to stamp')
@click.option('--revision', '-r', default='head', help='Revision to stamp (default: head)')
def stamp(database, revision):
    """Stamp database with revision (mark as migrated without running)"""
    databases = [database] if database != 'all' else list(DATABASES.keys())
    
    for db in databases:
        console.print(f"[cyan]Stamping {db} with {revision}...[/cyan]")
        
        if not check_database_connection(db):
            console.print(f"[red]Connection failed for {db}[/red]")
            continue
        
        stdout, stderr, code = run_alembic_command(['stamp', revision], db)
        
        if code == 0:
            console.print(f"[green]✓ {db} stamped successfully[/green]")
        else:
            console.print(f"[red]✗ Failed to stamp {db}: {stderr}[/red]")

@cli.command()
def info():
    """Show database information"""
    table = Table(title="MAMS Database Configuration")
    table.add_column("Database", style="cyan", no_wrap=True)
    table.add_column("Description", style="magenta")
    table.add_column("Connection", style="green")
    
    for db_name, config in DATABASES.items():
        # Test connection
        connection_status = "[green]Connected[/green]" if check_database_connection(db_name) else "[red]Failed[/red]"
        table.add_row(db_name, config['description'], connection_status)
    
    console.print(table)

if __name__ == '__main__':
    cli()