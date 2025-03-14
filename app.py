from flask import Flask, render_template, url_for, session, redirect, request, jsonify, send_file
from google_auth_oauthlib.flow import Flow
from pip._vendor import cachecontrol
import google.auth.transport.requests
from google.oauth2 import id_token
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
import os
import io
import pathlib
import requests
import json
import google.oauth2.credentials
import tempfile
import zipfile
        
app = Flask(__name__)
app.secret_key = "random-secret-key"  

# Google OAuth2 credentials
CLIENT_SECRETS_FILE = "client_secret.json"  # Download this from GCP
GOOGLE_CLIENT_ID = "9792465820-qnvrp2qh51v9ssbeehgmn819h3s88641.apps.googleusercontent.com" # Replace with your own client ID from GCP

# OAuth2 configuration with Drive scope
flow = Flow.from_client_secrets_file(
    client_secrets_file=CLIENT_SECRETS_FILE,
        scopes=[
        "https://www.googleapis.com/auth/userinfo.profile", 
        "https://www.googleapis.com/auth/userinfo.email", 
        "openid",
        "https://www.googleapis.com/auth/drive"  # Full Drive access scope 
    ],
    redirect_uri="https://app-diagrams-net.onrender.com/callback"
)

@app.route("/")
def index():
    return render_template('index.html')

@app.route("/login")
def login():
    authorization_url, state = flow.authorization_url(
        # Enable offline access so we can get a refresh token
        access_type='offline',
        # Enable incremental authorization
        include_granted_scopes='true',
        # Force the consent prompt to ensure we get a refresh token
        prompt='consent'
    )
    session["state"] = state
    return redirect(authorization_url)

@app.route("/callback")
def callback():
    try:
        flow.fetch_token(authorization_response=request.url)
        
        if not session.get("state") == request.args.get("state"):
            return redirect(url_for("index"))  # State doesn't match!
        
        credentials = flow.credentials
        session['credentials'] = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes
        }
        
        # Get user info directly from the userinfo endpoint
        userinfo_endpoint = "https://www.googleapis.com/oauth2/v3/userinfo"
        auth_header = {"Authorization": f"Bearer {credentials.token}"}
        userinfo_response = requests.get(userinfo_endpoint, headers=auth_header)
        
        if userinfo_response.status_code != 200:
            return "Error fetching user info", 500
            
        userinfo = userinfo_response.json()
        session["google_id"] = userinfo.get("sub")
        session["name"] = userinfo.get("name")
        session["email"] = userinfo.get("email")
        
        # Render your existing landing page
        try:
            # Try to render landing.html with detailed error logging
            return render_template('landing.html')
        except Exception as template_error:
            print(f"Template rendering error: {template_error}")
            return f"Authentication successful, but landing page could not be rendered. Error: {str(template_error)}", 500
        
    except Exception as e:

        print(f"Callback error: {e}")
        return f"Authentication error: {str(e)}", 500

@app.route("/drive")
def drive():
    if 'credentials' not in session:
        return redirect(url_for('login'))
    
    # Build the Drive API service
    try:
        credentials = google.oauth2.credentials.Credentials(**session['credentials'])
        drive_service = build('drive', 'v3', credentials=credentials)
        
        # Call the Drive API to list files
        results = drive_service.files().list(
            pageSize=100,
            fields="nextPageToken, files(id, name, mimeType, modifiedTime, size)",
            orderBy="modifiedTime desc"
        ).execute()
        
        files = results.get('files', [])
        
        # For each file, get its collaborators
        for file in files:
            try:
                # Get permissions (collaborators) for this file
                permissions = drive_service.permissions().list(
                    fileId=file['id'],
                    fields="permissions(id,emailAddress,role,displayName)"
                ).execute()
                
                # Add permissions to the file object
                file['collaborators'] = permissions.get('permissions', [])
            except Exception as e:
                print(f"Error getting permissions for file {file['id']}: {str(e)}")
                file['collaborators'] = []
        
        # Update credentials in session in case they were refreshed
        session['credentials'] = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes
        }
        
        # Check if this is an API request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"files": files})
        
        return render_template('drive.html', files=files)
    
    except Exception as e:
        print(f"Drive access error: {e}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"error": str(e)}), 500
        return f"Error accessing Drive: {str(e)}", 500

@app.route("/drive/add_collaborator", methods=["POST"])
def add_collaborator():
    if 'credentials' not in session:
        return jsonify({"error": "Not logged in"}), 401
    
    data = request.get_json()
    file_id = data.get("file_id")
    email = data.get("email")
    
    if not file_id or not email:
        return jsonify({"error": "Missing required parameters"}), 400
    
    try:
        credentials = google.oauth2.credentials.Credentials(**session['credentials'])
        drive_service = build('drive', 'v3', credentials=credentials)
        
        permission = {"type": "user", "role": "writer", "emailAddress": email}
        drive_service.permissions().create(
            fileId=file_id, 
            body=permission,
            sendNotificationEmail=True
        ).execute()
        
        # Update credentials in session
        session['credentials'] = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes
        }
        
        return jsonify({
            "success": True, 
            "message": f"Added {email} as collaborator to {file_id}"
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500
        
@app.route("/drive/remove_collaborator", methods=["POST"])
def remove_collaborator():
    if 'credentials' not in session:
        return jsonify({"error": "Not logged in"}), 401
    
    data = request.get_json()
    file_id = data.get("file_id")
    email = data.get("email")
    
    if not file_id or not email:
        return jsonify({"error": "Missing required parameters"}), 400
    
    try:
        credentials = google.oauth2.credentials.Credentials(**session['credentials'])
        drive_service = build('drive', 'v3', credentials=credentials)
        
        # List permissions to find the right one
        permissions_response = drive_service.permissions().list(
            fileId=file_id,
            fields="permissions(id,emailAddress)"
        ).execute()
        
        permissions = permissions_response.get("permissions", [])
        print(f"Found permissions: {permissions}")
        
        permission_id = None
        email_lower = email.lower()  # Convert to lowercase for case-insensitive comparison
        
        for perm in permissions:
            perm_email = perm.get("emailAddress", "").lower()
            if perm_email == email_lower:
                permission_id = perm["id"]
                break
        
        if not permission_id:
            return jsonify({"error": f"Email {email} not found as a collaborator"}), 404
        
        # Try using supportsAllDrives parameter
        drive_service.permissions().delete(
            fileId=file_id, 
            permissionId=permission_id,
            supportsAllDrives=True
        ).execute()
        
        # Update credentials in session
        session['credentials'] = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes
        }
        
        return jsonify({
            "success": True, 
            "message": f"Removed {email} from {file_id}"
        })
    
    except Exception as e:
        import traceback
        print(f"Error removing collaborator: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

# Route for deleting files
@app.route("/drive/delete_file", methods=["POST"])
def delete_file():
    if 'credentials' not in session:
        return jsonify({"error": "Not logged in"}), 401
    
    data = request.get_json()
    file_id = data.get("file_id")
    
    if not file_id:
        return jsonify({"error": "Missing file_id parameter"}), 400
    
    try:
        credentials = google.oauth2.credentials.Credentials(**session['credentials'])
        drive_service = build('drive', 'v3', credentials=credentials)
        
        drive_service.files().delete(fileId=file_id).execute()
        
        # Update credentials in session
        session['credentials'] = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes
        }
        
        return jsonify({
            "success": True, 
            "message": f"Deleted file/folder: {file_id}"
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Route for uploading files
@app.route("/drive/upload", methods=["POST"])
def upload_file():
    if 'credentials' not in session:
        return jsonify({"error": "Not logged in"}), 401
    
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    parent_folder = request.form.get('parent_folder', None)
    
    try:
        credentials = google.oauth2.credentials.Credentials(**session['credentials'])
        drive_service = build('drive', 'v3', credentials=credentials)
        
        # Save file temporarily
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        temp_path = temp_file.name
        temp_file.close()
        file.save(temp_path)
        
        # Get mime type
        mime_type = file.content_type or 'application/octet-stream'
        
        # Prepare metadata
        file_metadata = {"name": file.filename}
        if parent_folder:
            file_metadata["parents"] = [parent_folder]
        
        # Upload file
        media = MediaFileUpload(temp_path, mimetype=mime_type)
        uploaded_file = drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id,name,mimeType,webViewLink"
        ).execute()
        
        # Remove temporary file
        os.unlink(temp_path)
        
        # Update credentials in session
        session['credentials'] = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes
        }
        
        return jsonify({
            "success": True,
            "message": "File uploaded successfully",
            "file": uploaded_file
        })
    
    except Exception as e:
        # Make sure to remove temp file even if upload fails
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.unlink(temp_path)
        return jsonify({"error": str(e)}), 500



def get_drive_service():
    """Get an authenticated Drive service using credentials from the session"""
    if 'credentials' not in session:
        return None  # or raise an exception
    
    try:
        credentials = google.oauth2.credentials.Credentials(**session['credentials'])
        drive_service = build('drive', 'v3', credentials=credentials)
        
        # Update credentials in session in case they were refreshed
        session['credentials'] = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes
        }
        
        return drive_service
    
    except Exception as e:
        print(f"Error getting Drive service: {e}")
        return None  # or raise an exception



# Then fix the download_zip function
@app.route("/drive/download_zip", methods=["POST"])
def download_zip():
    """Download selected files as a ZIP archive"""
    if 'credentials' not in session:
        return jsonify({"error": "Not logged in"}), 401
    
    drive_service = get_drive_service()
    if not drive_service:
        return jsonify({"error": "Failed to initialize Drive service"}), 500
    
    # Get request data
    try:
        # Handle both form submission and JSON data
        if request.content_type and 'application/json' in request.content_type:
            data = request.get_json() or {}
            file_ids = data.get("file_ids", [])
        else:
            file_ids = request.form.getlist('file_ids') or []
            # Handle case where file_ids might be a JSON string
            if len(file_ids) == 1 and file_ids[0].startswith('['):
                try:
                    file_ids = json.loads(file_ids[0])
                except:
                    pass
    except Exception as e:
        return jsonify({"error": f"Error parsing request: {str(e)}"}), 400
    
    if not file_ids:
        return jsonify({"error": "No files selected"}), 400
    
    # Create a ZIP file in memory
    memory_file = io.BytesIO()
    try:
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file_id in file_ids:
                try:
                    # Get file metadata
                    file_metadata = drive_service.files().get(fileId=file_id).execute()
                    file_name = file_metadata.get('name', 'unnamed-file')
                    mime_type = file_metadata.get('mimeType', '')
                    
                    # Skip folders - they can't be downloaded directly
                    if mime_type == 'application/vnd.google-apps.folder':
                        print(f"Skipping folder: {file_name}")
                        continue
                    
                    # Handle Google Docs, Sheets, Slides, etc.
                    export_formats = {
                        'application/vnd.google-apps.document': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                        'application/vnd.google-apps.spreadsheet': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                        'application/vnd.google-apps.presentation': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
                        'application/vnd.google-apps.drawing': 'application/pdf',
                    }
                    
                    file_content = io.BytesIO()
                    
                    if mime_type.startswith('application/vnd.google-apps') and mime_type in export_formats:
                        # This is a Google Doc/Sheet/Slide, which needs to be exported
                        export_mime_type = export_formats[mime_type]
                        
                        # Set appropriate file extension
                        extensions = {
                            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
                            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '.xlsx',
                            'application/vnd.openxmlformats-officedocument.presentationml.presentation': '.pptx',
                            'application/pdf': '.pdf',
                        }
                        
                        if export_mime_type in extensions:
                            if not file_name.endswith(extensions[export_mime_type]):
                                file_name += extensions[export_mime_type]
                        
                        # Export the file
                        print(f"Exporting {file_name} as {export_mime_type}")
                        request = drive_service.files().export_media(fileId=file_id, mimeType=export_mime_type)
                        downloader = MediaIoBaseDownload(file_content, request)
                    else:
                        # Regular file, download directly
                        print(f"Downloading {file_name} ({mime_type})")
                        request = drive_service.files().get_media(fileId=file_id)
                        downloader = MediaIoBaseDownload(file_content, request)
                    
                    # Download the file
                    done = False
                    while not done:
                        status, done = downloader.next_chunk()
                        print(f"Download progress: {int(status.progress() * 100)}%")
                    
                    # Reset the file pointer to the beginning
                    file_content.seek(0)
                    
                    # Add file to the ZIP
                    zf.writestr(file_name, file_content.read())
                    print(f"Added {file_name} to ZIP")
                    
                except Exception as e:
                    # Log error but continue with other files
                    print(f"Error downloading file {file_id}: {str(e)}")
        
        # Prepare the ZIP file for download
        memory_file.seek(0)
        
        # Set the filename to include the current date/time
        import datetime
        current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"drive_files_{current_time}.zip"
        
        return send_file(
            memory_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name=filename  # Use download_name for Flask 2.0+, otherwise use attachment_filename
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Error creating ZIP: {str(e)}"}), 500

@app.route("/drive/remove_all_collaborators", methods=["POST"])
def remove_all_collaborators():
    """Remove all collaborators from a file except the owner"""
    if 'credentials' not in session:
        return jsonify({"error": "Not logged in"}), 401
    
    drive_service = get_drive_service()
    if not drive_service:
        return jsonify({"error": "Failed to initialize Drive service"}), 500
    
    # Get request data
    data = request.get_json()
    file_id = data.get("file_id")
    
    if not file_id:
        return jsonify({"error": "Missing file_id parameter"}), 400
    
    try:
        # Get all permissions for the file
        permissions = drive_service.permissions().list(
            fileId=file_id,
            fields="permissions(id,emailAddress,role)"
        ).execute().get("permissions", [])
        
        removed_count = 0
        owner_email = None
        
        # Find the owner's email first
        for perm in permissions:
            if perm.get("role") == "owner":
                owner_email = perm.get("emailAddress")
                break
        
        # Then remove all non-owner permissions
        for perm in permissions:
            # Skip the owner permission
            if perm.get("role") == "owner":
                continue
                
            # Delete all non-owner permissions
            drive_service.permissions().delete(
                fileId=file_id, 
                permissionId=perm["id"],
                supportsAllDrives=True  # Add this parameter to support shared drives
            ).execute()
            removed_count += 1
        
        return jsonify({
            "success": True,
            "message": f"Removed {removed_count} collaborators from file {file_id}",
            "removed_count": removed_count,
            "owner": owner_email
        })
    except Exception as e:
        import traceback
        print(f"Error removing collaborators: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == "__main__":
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"  # Only for development
    app.run(debug=True)
