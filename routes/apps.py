from flask import Blueprint, render_template, request, redirect, url_for, flash, Response
from models import db
from routes.auth import login_required, role_required, get_current_admin
import os

apps_bp = Blueprint('apps', __name__)


@apps_bp.route('/apps')
@login_required
@role_required('superadmin', 'admin')
def index():
    admin = get_current_admin()
    if admin['role'] == 'superadmin':
        apps = db.get_apps()
    else:
        apps = db.get_apps()
    return render_template('apps.html', admin=admin, apps=apps)


@apps_bp.route('/apps/create', methods=['POST'])
@login_required
@role_required('superadmin', 'admin')
def create():
    admin = get_current_admin()
    name = request.form.get('name', '').strip()
    if not name:
        flash('App name is required.', 'error')
    else:
        app_id = db.create_app(name, str(admin['_id']))
        flash(f'Application "{name}" created!', 'success')
    return redirect(url_for('apps.index'))


@apps_bp.route('/apps/delete/<app_id>', methods=['POST'])
@login_required
@role_required('superadmin', 'admin')
def delete(app_id):
    db.delete_app(app_id)
    flash('Application deleted.', 'success')
    return redirect(url_for('apps.index'))


@apps_bp.route('/apps/toggle/<app_id>', methods=['POST'])
@login_required
@role_required('superadmin', 'admin')
def toggle(app_id):
    db.toggle_app(app_id)
    flash('Application status updated.', 'success')
    return redirect(url_for('apps.index'))


@apps_bp.route('/apps/update_version/<app_id>', methods=['POST'])
@login_required
@role_required('superadmin', 'admin')
def update_version(app_id):
    version = request.form.get('version', '').strip()
    if version:
        db.update_app_version(app_id, version)
        flash('Application version updated.', 'success')
    else:
        flash('Version cannot be empty.', 'error')
    return redirect(url_for('apps.manage', app_id=app_id))


@apps_bp.route('/apps/manage/<app_id>')
@login_required
@role_required('superadmin', 'admin')
def manage(app_id):
    """Display detailed app management page with SDK download options."""
    admin = get_current_admin()
    app = db.get_app_by_id(app_id)
    if not app:
        flash('Application not found.', 'error')
        return redirect(url_for('apps.index'))
    
    # Get owner info
    owner = db.get_admin_by_id(str(app['owner_id']))
    
    # Build API URL from request
    api_url = f"{request.scheme}://{request.host}/api/v1"
    
    return render_template('manage_app.html', 
                         admin=admin, 
                         app=app, 
                         owner=owner,
                         api_url=api_url)


@apps_bp.route('/apps/download-sdk/<app_id>/<language>')
@login_required
@role_required('superadmin', 'admin')
def download_sdk(app_id, language):
    """Generate and download SDK file with pre-filled credentials."""
    app = db.get_app_by_id(app_id)
    if not app:
        flash('Application not found.', 'error')
        return redirect(url_for('apps.index'))
    
    # Build API URL
    api_url = f"{request.scheme}://{request.host}/api/v1"
    version = app.get('version', '1.0.0')
    
    # SDK templates directory
    sdk_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'sdk')
    
    # Map language to file info
    sdk_files = {
        'python': ('neutron_sdk.py', 'text/x-python', f'{app["name"]}_sdk.py'),
        'csharp': ('KeyAuth.cs', 'text/plain', 'KeyAuth.cs'),
        'cpp': ('KeyAuth.hpp', 'text/plain', 'KeyAuth.hpp'),
    }
    
    if language not in sdk_files:
        flash('Invalid SDK language.', 'error')
        return redirect(url_for('apps.manage', app_id=app_id))
    
    template_file, content_type, download_name = sdk_files[language]
    template_path = os.path.join(sdk_dir, template_file)
    
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Replace placeholders with actual values
        content = content.replace('{{API_URL}}', api_url)
        content = content.replace('{{APP_SECRET}}', app['secret_key'])
        content = content.replace('{{APP_NAME}}', app['name'])
        content = content.replace('{{OWNER_ID}}', str(app['owner_id']))
        content = content.replace('{{VERSION}}', version)
        
        return Response(
            content,
            mimetype=content_type,
            headers={'Content-Disposition': f'attachment; filename={download_name}'}
        )
    except Exception as e:
        flash(f'Error generating SDK: {str(e)}', 'error')
        return redirect(url_for('apps.manage', app_id=app_id))
