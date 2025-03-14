<!DOCTYPE html>
<html>

<head>
    <title>Google Drive Files</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.8.1/font/bootstrap-icons.css">
    <style>
        .action-panel {
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }

        .checkbox-col {
            width: 40px;
        }
    </style>
</head>

<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
        <div class="container">
            <a class="navbar-brand" href="/">Diagrams.net</a>
            <div class="navbar-nav ms-auto">
                {% if session.get('email') %}
                <span class="nav-link text-light">{{ session.get('email') }}</span>
                <a class="nav-link" href="/logout">Logout</a>
                {% else %}
                <a class="nav-link" href="/login">Login</a>
                {% endif %}
            </div>
        </div>
    </nav>

    <div class="container mt-5">
        {% if session.get('email') %}
        <div class="d-flex justify-content-between align-items-center mb-4">
            <h2>Google Drive File Manager</h2>
            <div>
                <button class="btn btn-primary" onclick="window.location.reload()">
                    <i class="bi bi-arrow-clockwise"></i> Refresh Files
                </button>
            </div>
        </div>

        <!-- Action Panel -->
        <div class="action-panel">
            <div class="row g-3">

                <div class="col-md-6">
                    <form id="upload-form" enctype="multipart/form-data">
                        <div class="input-group">
                            <input type="file" class="form-control" id="file-upload" name="file">
                            <button class="btn btn-primary" type="button" onclick="uploadFile()">
                                <i class="bi bi-cloud-upload"></i> Upload
                            </button>
                        </div>
                    </form>
                    <div class="mt-2" id="upload-progress" style="display:none;">
                        <div class="progress">
                            <div class="progress-bar progress-bar-striped progress-bar-animated" style="width: 100%">
                            </div>
                        </div>
                    </div>
                </div>
                

                <div class="col-md-6">
                    <div class="d-grid gap-2 d-md-flex justify-content-md-end">
                       
                        <button class="btn btn-secondary" onclick="downloadAsZip()">
                            <i class="bi bi-file-earmark-zip"></i> Download as ZIP
                        </button>
                        <button class="btn btn-warning" onclick="removeAllCollaborators()">
                            <i class="bi bi-people-fill"></i> Remove All Collaborators
                        </button>
                        <button class="btn btn-danger" onclick="deleteSelected()">
                            <i class="bi bi-trash"></i> Delete Selected
                        </button>
                    </div>
                </div>
            </div>

            <hr>

        </div>

        {% if files %}
        <div class="table-responsive">
            <table class="table table-striped table-hover" id="files-table">
                <thead class="table-dark">
                    <tr>
                        <th class="checkbox-col">
                            <input type="checkbox" id="select-all" class="form-check-input"
                                onchange="toggleSelectAll()">
                        </th>
                        <th>Name</th>
                        <th>Type</th>
                        <th>Last Modified</th>
                        <th>Size</th>
                        <th>Actions</th>
                        <th>Collaborators</th>
                    </tr>
                </thead>
                <tbody>
                    {% for file in files %}
                    <tr>
                        <td>
                            <input type="checkbox" class="form-check-input file-checkbox" data-file-id="{{ file.id }}">
                        </td>
                        <td>{{ file.name }}</td>
                        <td>
                            {% if 'folder' in file.mimeType %}
                            <i class="bi bi-folder-fill text-warning"></i> Folder
                            {% else %}
                            <i class="bi bi-file-earmark-text"></i> {{ file.mimeType.split('/')[-1] }}
                            {% endif %}
                        </td>
                        <td>{{ file.modifiedTime.split('T')[0] }}</td>
                        <td>
                            {% if file.size %}
                            {{ (file.size|int / 1024)|round(1) }} KB
                            {% else %}
                            -
                            {% endif %}
                        </td>
                        <td>
                            <div class="btn-group btn-group-sm">
                                <a href="https://drive.google.com/file/d/{{ file.id }}/view" target="_blank"
                                    class="btn btn-outline-primary">
                                    <i class="bi bi-eye"></i>
                                </a>
                                <button class="btn btn-outline-danger" onclick="deleteFile('{{ file.id }}')">
                                    <i class="bi bi-trash"></i>
                                </button>
                                <button class="btn btn-outline-success" onclick="showAddCollaborator('{{ file.id }}')">
                                    <i class="bi bi-share"></i>
                                </button>
                                <button class="btn btn-outline-warning" onclick="confirmRemoveAllCollaborators('{{ file.id }}')">
                                    <i class="bi bi-people-fill"></i>
                                </button>
                            </div>
                        </td>
                        <td>
                            {% if file.collaborators %}
                                <div class="dropdown">
                                    <button class="btn btn-sm btn-outline-secondary dropdown-toggle" type="button" data-bs-toggle="dropdown" aria-expanded="false">
                                        {{ file.collaborators|length }} Collaborator(s)
                                    </button>
                                    <ul class="dropdown-menu p-2" style="max-width: 250px;">
                                        {% for collaborator in file.collaborators %}
                                            <li class="d-flex align-items-center py-1">
                                                <div class="flex-grow-1 text-truncate me-2">
                                                    <span>{{ collaborator.emailAddress }}</span>
                                                    <small class="d-block text-muted">{{ collaborator.role }}</small>
                                                </div>
                                                <button class="btn btn-sm py-0 px-1" 
                                                        onclick="removeSpecificCollaborator('{{ file.id }}', '{{ collaborator.emailAddress }}')">
                                                    <i class="bi bi-x-circle text-danger" style="font-size: 0.8rem;"></i>
                                                </button>
                                            </li>
                                            {% if not loop.last %}<li><hr class="dropdown-divider my-1"></li>{% endif %}
                                        {% endfor %}
                                    </ul>
                                </div>
                            {% else %}
                                <span class="text-muted">No collaborators</span>
                            {% endif %}
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        {% else %}
        <div class="alert alert-info">
            No files found in your Google Drive.
        </div>
        {% endif %}
        {% else %}
        <div class="alert alert-warning">
            Please <a href="/login">login</a> to view your Google Drive files.
        </div>
        {% endif %}
    </div>

    <!-- Toast Notifications -->
    <div class="position-fixed bottom-0 end-0 p-3" style="z-index: 11">
        <div id="toast-container"></div>
    </div>

    <!-- Add collaborator modal -->
    <div class="modal fade" id="collaboratorModal" tabindex="-1" aria-hidden="true">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Add Collaborator</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body">
                    <div class="mb-3">
                        <label for="modal-email" class="form-label">Email address</label>
                        <input type="email" class="form-control" id="modal-email">
                        <input type="hidden" id="modal-file-id">
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                    <button type="button" class="btn btn-primary" onclick="addSingleCollaborator()">Add
                        Collaborator</button>
                </div>
            </div>
        </div>
    </div>

    <!-- Remove All Collaborators Confirmation Modal -->
    <div class="modal fade" id="removeAllCollaboratorsModal" tabindex="-1" aria-hidden="true">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Remove All Collaborators</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body">
                    <p>Are you sure you want to remove <strong>ALL</strong> collaborators from this file?</p>
                    <p>This will remove everyone except you (the owner).</p>
                    <input type="hidden" id="remove-all-file-id">
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                    <button type="button" class="btn btn-danger" onclick="executeRemoveAllCollaborators()">
                        <i class="bi bi-exclamation-triangle"></i> Remove All Collaborators
                    </button>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        // Get all selected file IDs
        function getSelectedFileIds() {
            const checkboxes = document.querySelectorAll('.file-checkbox:checked');
            return Array.from(checkboxes).map(checkbox => checkbox.getAttribute('data-file-id'));
        }

        // Toggle select all checkbox functionality
        function toggleSelectAll() {
            const selectAll = document.getElementById('select-all');
            const fileCheckboxes = document.querySelectorAll('.file-checkbox');

            fileCheckboxes.forEach(checkbox => {
                checkbox.checked = selectAll.checked;
            });
        }

        // Download selected files as ZIP
        function downloadAsZip() {
            const fileIds = getSelectedFileIds();

            if (fileIds.length === 0) {
                showToast('Please select at least one file', 'warning');
                return;
            }

            showToast('Preparing ZIP file for download...', 'info');

            // Create a form to submit the request
            const form = document.createElement('form');
            form.method = 'POST';
            form.action = '/drive/download_zip';
            form.style.display = 'none';

            // Create a hidden input for the file IDs
            const input = document.createElement('input');
            input.type = 'hidden';
            input.name = 'file_ids';
            input.value = JSON.stringify(fileIds);
            form.appendChild(input);

            // Add the form to the document and submit it
            document.body.appendChild(form);
            form.submit();

            // Clean up
            setTimeout(() => {
                document.body.removeChild(form);
            }, 2000);
        }

        // Function to show the remove all collaborators confirmation modal
        function confirmRemoveAllCollaborators(fileId) {
            document.getElementById('remove-all-file-id').value = fileId;
            const modal = new bootstrap.Modal(document.getElementById('removeAllCollaboratorsModal'));
            modal.show();
        }

        // Function to remove all collaborators from selected files
        function removeAllCollaborators() {
            const fileIds = getSelectedFileIds();

            if (fileIds.length === 0) {
                showToast('Please select at least one file', 'warning');
                return;
            }

            if (!confirm(`Are you sure you want to remove ALL collaborators from ${fileIds.length} selected file(s)?`)) {
                return;
            }

            // Show a progress toast
            showToast(`Removing all collaborators from ${fileIds.length} file(s)...`, 'info');

            const promises = fileIds.map(fileId => {
                return fetch('/drive/remove_all_collaborators', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        file_id: fileId
                    })
                })
                    .then(response => {
                        if (!response.ok) {
                            throw new Error(`HTTP error ${response.status}`);
                        }
                        return response.json();
                    });
            });

            Promise.all(promises)
                .then(results => {
                    // Calculate total removed
                    const totalRemoved = results.reduce((acc, result) => acc + (result.removed_count || 0), 0);
                    showToast(`Removed ${totalRemoved} collaborators from ${fileIds.length} file(s)`);

                    // Reload the page after a short delay
                    setTimeout(() => {
                        window.location.reload();
                    }, 1500);
                })
                .catch(error => {
                    console.error('Error:', error);
                    showToast(`Error removing collaborators: ${error.message}`, 'danger');
                });
        }

        // Function to execute removing all collaborators for a single file
        function executeRemoveAllCollaborators() {
            const fileId = document.getElementById('remove-all-file-id').value;

            fetch('/drive/remove_all_collaborators', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    file_id: fileId
                })
            })
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP error ${response.status}`);
                    }
                    return response.json();
                })
                .then(data => {
                    showToast(`Removed ${data.removed_count} collaborators successfully`);
                    bootstrap.Modal.getInstance(document.getElementById('removeAllCollaboratorsModal')).hide();
                    
                    // Reload the page after a short delay
                    setTimeout(() => {
                        window.location.reload();
                    }, 1000);
                })
                .catch(error => {
                    console.error('Error:', error);
                    showToast(`Error removing collaborators: ${error.message}`, 'danger');
                });
        }

        // Add this function to your JavaScript section
        function removeSpecificCollaborator(fileId, email) {
            if (!confirm(`Are you sure you want to remove ${email} from this file?`)) {
                return;
            }

            fetch('/drive/remove_collaborator', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    file_id: fileId,
                    email: email
                })
            })
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP error ${response.status}`);
                    }
                    return response.json();
                })
                .then(data => {
                    showToast(`Removed ${email} as collaborator`);

                    // Reload the page to refresh the collaborator list
                    setTimeout(() => {
                        window.location.reload();
                    }, 1000);
                })
                .catch(error => {
                    console.error('Error:', error);
                    showToast(`Error removing collaborator: ${error.message}`, 'danger');
                });
        }

        // Show toast notification
        function showToast(message, type = 'success') {
            const container = document.getElementById('toast-container');
            const toastId = 'toast-' + Date.now();

            const toastHtml = `
                <div id="${toastId}" class="toast align-items-center text-white bg-${type} border-0" role="alert" aria-live="assertive" aria-atomic="true">
                    <div class="d-flex">
                        <div class="toast-body">
                            ${message}
                        </div>
                        <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
                    </div>
                </div>
            `;

            container.insertAdjacentHTML('beforeend', toastHtml);
            const toastElement = bootstrap.Toast.getOrCreateInstance(document.getElementById(toastId));
            toastElement.show();

            // Auto remove after shown
            const toast = document.getElementById(toastId);
            toast.addEventListener('hidden.bs.toast', () => {
                toast.remove();
            });
        }

        // Add collaborator to selected files
        function addCollaborator() {
            const fileIds = getSelectedFileIds();
            const email = document.getElementById('collaborator-email').value.trim();

            if (!email) {
                showToast('Please enter an email address', 'danger');
                return;
            }

            if (fileIds.length === 0) {
                showToast('Please select at least one file', 'warning');
                return;
            }

            const promises = fileIds.map(fileId => {
                return fetch('/drive/add_collaborator', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        file_id: fileId,
                        email: email
                    })
                })
                    .then(response => response.json());
            });

            Promise.all(promises)
                .then(results => {
                    showToast(`Added ${email} as collaborator to ${fileIds.length} file(s)`);
                    document.getElementById('collaborator-email').value = '';
                })
                .catch(error => {
                    showToast('Error adding collaborator: ' + error, 'danger');
                });
        }

        // Show modal for adding collaborator to single file
        function showAddCollaborator(fileId) {
            document.getElementById('modal-file-id').value = fileId;
            document.getElementById('modal-email').value = '';
            const modal = new bootstrap.Modal(document.getElementById('collaboratorModal'));
            modal.show();
        }

        // Add collaborator to single file (from modal)
        function addSingleCollaborator() {
            const fileId = document.getElementById('modal-file-id').value;
            const email = document.getElementById('modal-email').value.trim();

            if (!email) {
                showToast('Please enter an email address', 'danger');
                return;
            }

            fetch('/drive/add_collaborator', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    file_id: fileId,
                    email: email
                })
            })
                .then(response => response.json())
                .then(data => {
                    showToast(`Added ${email} as collaborator`);
                    bootstrap.Modal.getInstance(document.getElementById('collaboratorModal')).hide();
                })
                .catch(error => {
                    showToast('Error adding collaborator: ' + error, 'danger');
                });
        }

        // Updated removeCollaborator function with better error handling and page reload
        function removeCollaborator() {
            const fileIds = getSelectedFileIds();
            const email = document.getElementById('remove-email').value.trim();

            if (!email) {
                showToast('Please enter an email address', 'danger');
                return;
            }

            if (fileIds.length === 0) {
                showToast('Please select at least one file', 'warning');
                return;
            }

            if (!confirm(`Are you sure you want to remove ${email} from ${fileIds.length} file(s)?`)) {
                return;
            }

            // Show a progress toast
            showToast(`Removing collaborator from ${fileIds.length} file(s)...`, 'info');

            const promises = fileIds.map(fileId => {
                return fetch('/drive/remove_collaborator', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        file_id: fileId,
                        email: email
                    })
                })
                    .then(response => {
                        if (!response.ok) {
                            throw new Error(`HTTP error ${response.status}`);
                        }
                        return response.json();
                    });
            });

            Promise.all(promises)
                .then(results => {
                    showToast(`Removed ${email} from ${fileIds.length} file(s)`);
                    document.getElementById('remove-email').value = '';

                    // Reload the page to reflect changes
                    setTimeout(() => {
                        window.location.reload();
                    }, 1000);
                })
                .catch(error => {
                    console.error('Error:', error);
                    showToast(`Error removing collaborator: ${error.message}`, 'danger');
                });
        }

        // Delete selected files
        function deleteSelected() {
            const fileIds = getSelectedFileIds();

            if (fileIds.length === 0) {
                showToast('Please select at least one file', 'warning');
                return;
            }

            if (!confirm(`Are you sure you want to delete ${fileIds.length} selected file(s)?`)) {
                return;
            }

            const promises = fileIds.map(fileId => {
                return fetch('/drive/delete', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        file_id: fileId
                    })
                })
                    .then(response => response.json());
            });

            Promise.all(promises)
                .then(results => {
                    showToast(`Deleted ${fileIds.length} file(s)`);
                    window.location.reload();
                })
                .catch(error => {
                    showToast('Error deleting files: ' + error, 'danger');
                });
        }

        // Delete a single file
        function deleteFile(fileId) {
            if (!confirm('Are you sure you want to delete this file?')) {
                return;
            }

            fetch('/drive/delete', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    file_id: fileId
                })
            })
                .then(response => response.json())
                .then(data => {
                    showToast('File deleted successfully');
                    window.location.reload();
                })
                .catch(error => {
                    showToast('Error deleting file: ' + error, 'danger');
                });
        }

        // Upload a file
        function uploadFile() {
            const fileInput = document.getElementById('file-upload');

            if (!fileInput.files || fileInput.files.length === 0) {
                showToast('Please select a file', 'warning');
                return;
            }

            const formData = new FormData();
            formData.append('file', fileInput.files[0]);

            // Show progress indicator
            document.getElementById('upload-progress').style.display = 'block';

            fetch('/drive/upload', {
                method: 'POST',
                body: formData
            })
                .then(response => response.json())
                .then(data => {
                    document.getElementById('upload-progress').style.display = 'none';
                    showToast('File uploaded successfully');
                    window.location.reload();
                })
                .catch(error => {
                    document.getElementById('upload-progress').style.display = 'none';
                    showToast('Error uploading file: ' + error, 'danger');
                });
        }
    </script>
</body>

</html>
