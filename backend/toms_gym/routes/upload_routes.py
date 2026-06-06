from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
import os
import logging
from datetime import datetime, timedelta
from toms_gym.storage import bucket, ALLOWED_EXTENSIONS
from toms_gym.db import get_db_connection
import sqlalchemy
import uuid
import traceback
import sys

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

upload_bp = Blueprint('upload', __name__)

# Frontend lift_type label -> database enum value. Shared by every upload path
# (multipart /upload and the signed-URL /upload/finalize) so the Plank mapping
# can't drift between them.
LIFT_TYPE_MAPPING = {
    "Squat": "Squat",
    "Bench": "Bench Press",  # "Bench" from frontend becomes "Bench Press" for database
    "Deadlift": "Deadlift",
    "BicepCurl": "Bicep Curl",
    "Clean": "Clean & Jerk",
    "Snatch": "snatch",
    "Overhead": "Overhead Press",
    "Plank": "Plank",
}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def _resolve_user_id(session, user_id, email):
    """Return a user_id, creating a minimal guest user from email if needed.

    Mirrors the email-based upload path: with only an email, find the existing
    user or create a minimal record. Falls back to '1' when neither is given.
    """
    if user_id:
        return user_id
    if email:
        existing = session.execute(
            sqlalchemy.text('SELECT id FROM "User" WHERE email = :email'),
            {"email": email}
        ).fetchone()
        if existing:
            return existing[0]
        new_id = str(uuid.uuid4())
        session.execute(
            sqlalchemy.text('''
                INSERT INTO "User" (id, email, name, username, auth_method, status, role, created_at)
                VALUES (:id, :email, :name, :username, 'password', 'active', 'user', NOW())
            '''),
            {"id": new_id, "email": email, "name": email.split('@')[0], "username": email}
        )
        session.commit()
        logger.info(f"Created guest user {new_id} for email {email}")
        return new_id
    return '1'


def _create_attempt_record(session, user_id, competition_id, database_lift_type, weight, video_url):
    """Find-or-create the UserCompetition, then insert a pending Attempt.

    Returns (attempt_id, user_competition_id). Commits within the passed
    session; caller owns rollback on failure.
    """
    user_competition = session.execute(
        sqlalchemy.text('''
            SELECT id FROM "UserCompetition"
            WHERE user_id = :user_id AND competition_id = :competition_id
        '''),
        {"user_id": user_id, "competition_id": competition_id}
    ).fetchone()

    if user_competition:
        user_competition_id = user_competition[0]
    else:
        user_competition_id = str(uuid.uuid4())
        prev = session.execute(
            sqlalchemy.text('''
                SELECT weight_class FROM "UserCompetition"
                WHERE user_id = :user_id ORDER BY created_at DESC LIMIT 1
            '''),
            {"user_id": user_id}
        ).fetchone()
        weight_class = prev[0] if prev else "85kg"
        session.execute(
            sqlalchemy.text('''
                INSERT INTO "UserCompetition" (id, user_id, competition_id, weight_class, gender)
                VALUES (:id, :user_id, :competition_id, :weight_class, :gender)
            '''),
            {"id": user_competition_id, "user_id": user_id, "competition_id": competition_id,
             "weight_class": weight_class, "gender": "male"}
        )
    session.commit()

    try:
        weight_kg = float(weight)
    except (ValueError, TypeError):
        logger.warning(f"Invalid weight value: {weight}, defaulting to 0")
        weight_kg = 0

    attempt_id = str(uuid.uuid4())
    session.execute(
        sqlalchemy.text('''
            INSERT INTO "Attempt" (id, user_competition_id, lift_type, weight_kg, status, video_url)
            VALUES (:id, :user_competition_id, :lift_type, :weight_kg, :status, :video_url)
        '''),
        {"id": attempt_id, "user_competition_id": user_competition_id,
         "lift_type": database_lift_type, "weight_kg": weight_kg,
         "status": "pending", "video_url": video_url}
    )
    session.commit()
    logger.info(f"Created attempt {attempt_id} (lift_type={database_lift_type})")
    return attempt_id, user_competition_id


def _generate_signed_upload_url(object_name, content_type, expires_minutes=15):
    """Generate a V4 signed PUT URL for direct-to-GCS upload.

    Cloud Run carries no private key, so signing goes through the IAM signBlob
    API using the runtime service account (which needs
    roles/iam.serviceAccountTokenCreator on itself). Returns (upload_url, public_url).
    """
    import google.auth
    from google.auth.transport.requests import Request as AuthRequest

    credentials, _ = google.auth.default()
    credentials.refresh(AuthRequest())

    blob = bucket.blob(object_name)
    upload_url = blob.generate_signed_url(
        version="v4",
        expiration=timedelta(minutes=expires_minutes),
        method="PUT",
        content_type=content_type,
        service_account_email=credentials.service_account_email,
        access_token=credentials.token,
    )
    public_url = f"https://storage.googleapis.com/{bucket.name}/{object_name}"
    return upload_url, public_url

@upload_bp.route('/upload', methods=['POST'])
def upload_video():
    logger.info("=== UPLOAD VIDEO FUNCTION STARTED ===")
    
    # Log request details
    logger.info(f"Request headers: {dict(request.headers)}")
    logger.info(f"Request form data: {dict(request.form)}")
    logger.info(f"Request files: {list(request.files.keys())}")
    
    if 'video' not in request.files:
        logger.error("No video file in request")
        return jsonify({'error': 'No video file provided'}), 400
        
    file = request.files['video']
    competition_id = request.form.get('competition_id', '1')  # Default to '1' if not provided
    user_id = request.form.get('user_id')  # No default - may come from email lookup
    email = request.form.get('email')  # New: email-based upload
    lift_type = request.form.get('lift_type', 'snatch')  # Default to 'snatch' if not provided
    weight = request.form.get('weight', '0')  # Default to '0' if not provided

    # Log received data
    logger.info(f"Received data - competition_id: {competition_id}, user_id: {user_id}, email: {email}")
    logger.info(f"Received data - lift_type: {lift_type}, weight: {weight}")
    
    # Map the lift type or default to "snatch" if not found
    database_lift_type = LIFT_TYPE_MAPPING.get(lift_type, "snatch")
    
    logger.info(f"Upload request received - user_id: {user_id}, competition_id: {competition_id}")
    logger.info(f"Original lift_type: {lift_type}, Mapped to DB lift_type: {database_lift_type}, weight: {weight}")
    
    if file.filename == '':
        logger.error("Empty filename")
        return jsonify({'error': 'No selected file'}), 400
        
    if not allowed_file(file.filename):
        logger.error(f"File type not allowed: {file.filename}")
        return jsonify({'error': 'File type not allowed'}), 400

    # Handle email-based upload: find or create user by email
    if email and not user_id:
        logger.info(f"Email-based upload: looking up user by email {email}")
        session = get_db_connection()
        try:
            # Find existing user by email
            user_result = session.execute(
                sqlalchemy.text('SELECT id FROM "User" WHERE email = :email'),
                {"email": email}
            ).fetchone()

            if user_result:
                user_id = user_result[0]
                logger.info(f"Found existing user with ID: {user_id}")
            else:
                # Create minimal user record
                user_id = str(uuid.uuid4())
                logger.info(f"Creating new user with ID: {user_id} for email: {email}")
                session.execute(
                    sqlalchemy.text('''
                        INSERT INTO "User" (id, email, name, username, auth_method, status, role, created_at)
                        VALUES (:id, :email, :name, :username, 'password', 'active', 'user', NOW())
                    '''),
                    {
                        "id": user_id,
                        "email": email,
                        "name": email.split('@')[0],  # Use email prefix as name
                        "username": email
                    }
                )
                session.commit()
                logger.info(f"Created new guest user with ID: {user_id}")
        except Exception as e:
            session.rollback()
            logger.error(f"Error finding/creating user by email: {str(e)}")
            return jsonify({'error': f'Failed to process email: {str(e)}'}), 500
        finally:
            session.close()

    # Fallback to default user_id if neither email nor user_id provided
    if not user_id:
        user_id = '1'
        logger.info("No email or user_id provided, using default user_id: 1")

    video_url = None
    attempt_id = None
    user_competition_id = None
        
    try:
        # Create a timestamp-based unique filename to avoid collisions
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        original_filename = secure_filename(file.filename)
        filename = f"videos/{timestamp}_{original_filename}"
        
        logger.info(f"Uploading file: {filename}")
        
        # Create a new blob and upload the file's content
        blob = bucket.blob(filename)
        content_type = file.content_type
        if not content_type or content_type == 'application/octet-stream':
            ext = original_filename.rsplit('.', 1)[-1].lower()
            content_type_map = {
                'mp4': 'video/mp4',
                'mov': 'video/quicktime',
                'avi': 'video/x-msvideo',
                'mkv': 'video/x-matroska',
                'webm': 'video/webm',
            }
            content_type = content_type_map.get(ext, content_type or 'application/octet-stream')
            logger.info(f"Inferred content type for upload: {content_type} (ext={ext})")
        blob.upload_from_string(
            file.read(),
            content_type=content_type
        )
        
        # Generate a URL for the file
        video_url = f"https://storage.googleapis.com/{bucket.name}/{filename}"
        
        logger.info(f"File uploaded successfully to URL: {video_url}")
        
        # Get the user_competition_id for the user and competition
        session = get_db_connection()
        logger.info(f"Database connection established.")
        
        try:
            # First, check if a UserCompetition record exists
            logger.info(f"Checking for existing UserCompetition record for user {user_id} and competition {competition_id}")
            user_competition_query = """
                SELECT id FROM "UserCompetition" 
                WHERE user_id = :user_id AND competition_id = :competition_id
            """
            
            user_competition = session.execute(
                sqlalchemy.text(user_competition_query),
                {"user_id": user_id, "competition_id": competition_id}
            ).fetchone()
            
            # If no UserCompetition exists, create one
            if not user_competition:
                logger.info(f"No UserCompetition found, creating new record")
                
                # Generate a UUID for the user competition
                usercomp_id = str(uuid.uuid4())
                
                # Get default weight class if possible
                weight_class_query = """
                    SELECT weight_class FROM "UserCompetition" 
                    WHERE user_id = :user_id 
                    ORDER BY created_at DESC LIMIT 1
                """
                
                weight_class_result = session.execute(
                    sqlalchemy.text(weight_class_query),
                    {"user_id": user_id}
                ).fetchone()
                
                weight_class = "85kg"  # Default weight class
                if weight_class_result:
                    weight_class = weight_class_result[0]
                    logger.info(f"Using weight class from previous competition: {weight_class}")
                else:
                    logger.info(f"Using default weight class: {weight_class}")
                
                # Create UserCompetition record
                insert_usercomp_query = """
                    INSERT INTO "UserCompetition" (id, user_id, competition_id, weight_class, gender)
                    VALUES (:id, :user_id, :competition_id, :weight_class, :gender)
                    RETURNING id
                """
                
                result = session.execute(
                    sqlalchemy.text(insert_usercomp_query),
                    {
                        "id": usercomp_id,
                        "user_id": user_id,
                        "competition_id": competition_id,
                        "weight_class": weight_class,
                        "gender": "male"  # Default gender
                    }
                )
                user_competition_id = usercomp_id
                logger.info(f"Created UserCompetition with ID: {user_competition_id}")
            else:
                user_competition_id = user_competition[0]
                logger.info(f"Found existing UserCompetition with ID: {user_competition_id}")
            
            # Create an attempt record with the video URL
            attempt_id = str(uuid.uuid4())
            logger.info(f"Creating new attempt with ID: {attempt_id}")
            
            # Convert weight to float safely
            try:
                weight_kg = float(weight)
                logger.info(f"Converted weight {weight} to float: {weight_kg}")
            except (ValueError, TypeError):
                logger.warning(f"Invalid weight value: {weight}, defaulting to 0")
                weight_kg = 0
                
            insert_attempt_query = """
                INSERT INTO "Attempt" (id, user_competition_id, lift_type, weight_kg, status, video_url)
                VALUES (:id, :user_competition_id, :lift_type, :weight_kg, :status, :video_url)
                RETURNING id
            """
            
            # Add additional logging before commit
            logger.info("Committing UserCompetition transaction")
            
            # Explicitly commit the UserCompetition transaction first
            session.commit()
            
            # Log the parameters for the insert attempt query for debugging
            insert_params = {
                "id": attempt_id,
                "user_competition_id": user_competition_id,
                "lift_type": database_lift_type,
                "weight_kg": weight_kg,
                "status": "pending",
                "video_url": video_url
            }
            logger.info(f"Attempt insert parameters: {insert_params}")
            
            # Now create the attempt
            logger.info("Executing attempt insert query")
            result = session.execute(
                sqlalchemy.text(insert_attempt_query),
                insert_params
            )
            
            # Explicitly commit the Attempt transaction
            logger.info("Committing Attempt transaction")
            session.commit()
            logger.info(f"Successfully created attempt record with ID: {attempt_id}")
            
            # Return the file information along with the attempt ID
            logger.info("=== UPLOAD VIDEO FUNCTION COMPLETED SUCCESSFULLY ===")
            return jsonify({
                'message': 'File uploaded successfully and attempt created',
                'url': video_url,
                'filename': filename,
                'attempt_id': attempt_id,
                'user_competition_id': user_competition_id,
                'user_id': str(user_id)
            }), 200
            
        except Exception as e:
            session.rollback()
            error_details = traceback.format_exc()
            logger.error(f"Database error: {str(e)}")
            logger.error(f"Error type: {type(e).__name__}")
            logger.error(f"Error details: {error_details}")
            
            # Print exception details to stderr for immediate visibility
            print(f"CRITICAL ERROR in upload_video: {str(e)}", file=sys.stderr)
            print(f"Error details: {error_details}", file=sys.stderr)
            
            # If we've already uploaded the file but failed to create the records,
            # return information about the uploaded file so it's not lost
            if video_url:
                logger.info("=== UPLOAD VIDEO FUNCTION COMPLETED WITH DATABASE ERROR ===")
                return jsonify({
                    'message': 'File uploaded but database record creation failed',
                    'error': str(e),
                    'url': video_url,
                    'filename': filename
                }), 500
            raise
        finally:
            session.close()
            logger.info("Database session closed")
        
    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"Upload error: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error details: {error_details}")
        
        # Print exception details to stderr for immediate visibility
        print(f"CRITICAL ERROR in upload_video: {str(e)}", file=sys.stderr)
        print(f"Error details: {error_details}", file=sys.stderr)
        
        logger.info("=== UPLOAD VIDEO FUNCTION COMPLETED WITH ERROR ===")
        return jsonify({'error': str(e)}), 500


@upload_bp.route('/upload/signed-url', methods=['POST'])
def create_signed_upload_url():
    """Mint a signed URL the browser can PUT a video straight to GCS with.

    Bypasses Cloud Run's 32 MiB request-body limit, which silently rejects
    large phone videos with a 413 at the proxy before Flask ever sees them.
    The browser uploads directly to GCS, then calls /upload/finalize.
    """
    data = request.get_json(silent=True) or {}
    filename = data.get('filename', '')
    content_type = data.get('content_type') or 'application/octet-stream'

    if not filename or not allowed_file(filename):
        logger.error(f"Signed-url request rejected, bad filename: {filename!r}")
        return jsonify({'error': 'File type not allowed'}), 400

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    object_name = f"videos/{timestamp}_{secure_filename(filename)}"

    try:
        upload_url, public_url = _generate_signed_upload_url(object_name, content_type)
    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"Failed to generate signed upload URL: {str(e)}")
        logger.error(error_details)
        return jsonify({'error': f'Could not create upload URL: {str(e)}'}), 500

    logger.info(f"Issued signed upload URL for {object_name} (type={content_type})")
    return jsonify({
        'upload_url': upload_url,
        'object_name': object_name,
        'public_url': public_url,
        'content_type': content_type,
    }), 200


@upload_bp.route('/upload/resumable-url', methods=['POST'])
def create_resumable_upload_url():
    """Start a GCS resumable upload session for large/unreliable uploads.

    The browser uploads the file in chunks to the returned session URI; a
    dropped connection resumes from the last confirmed byte instead of
    restarting. The session is created server-side with the runtime SA
    (no signing needed), and CORS-scoped to the caller's Origin so the
    browser's chunk PUTs are allowed. The browser calls /upload/finalize
    once the upload completes.
    """
    data = request.get_json(silent=True) or {}
    filename = data.get('filename', '')
    content_type = data.get('content_type') or 'application/octet-stream'

    if not filename or not allowed_file(filename):
        logger.error(f"Resumable-url request rejected, bad filename: {filename!r}")
        return jsonify({'error': 'File type not allowed'}), 400

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    object_name = f"videos/{timestamp}_{secure_filename(filename)}"
    origin = request.headers.get('Origin', '*')

    try:
        blob = bucket.blob(object_name)
        session_uri = blob.create_resumable_upload_session(
            content_type=content_type,
            origin=origin,
        )
    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"Failed to start resumable upload session: {str(e)}")
        logger.error(error_details)
        return jsonify({'error': f'Could not start upload: {str(e)}'}), 500

    public_url = f"https://storage.googleapis.com/{bucket.name}/{object_name}"
    logger.info(f"Started resumable session for {object_name} (type={content_type})")
    return jsonify({
        'session_uri': session_uri,
        'object_name': object_name,
        'public_url': public_url,
        'content_type': content_type,
    }), 200


@upload_bp.route('/upload/finalize', methods=['POST'])
def finalize_upload():
    """Create the Attempt after a successful direct-to-GCS upload.

    Runs the same user/UserCompetition/Attempt creation as /upload, but the
    bytes are already in GCS (uploaded via the signed URL), so there is no
    file in this request — only metadata.
    """
    data = request.get_json(silent=True) or {}
    object_name = data.get('object_name', '')
    public_url = data.get('public_url', '')
    competition_id = data.get('competition_id', '1')
    user_id = data.get('user_id')
    email = data.get('email')
    lift_type = data.get('lift_type', 'snatch')
    weight = data.get('weight', '0')

    logger.info(f"Finalize upload: object={object_name}, competition={competition_id}, "
                f"user_id={user_id}, email={email}, lift_type={lift_type}")

    if not object_name or not public_url:
        return jsonify({'error': 'Missing object_name or public_url'}), 400

    # Verify the upload actually landed in GCS before creating DB records,
    # so a failed/abandoned PUT can't leave an orphan Attempt with a dead URL.
    try:
        if not bucket.blob(object_name).exists():
            logger.error(f"Finalize rejected: blob {object_name} not found in GCS")
            return jsonify({'error': 'Uploaded file not found in storage'}), 400
    except Exception as e:
        # Don't hard-fail on a transient existence check; log and continue.
        logger.warning(f"Could not verify blob existence for {object_name}: {e}")

    database_lift_type = LIFT_TYPE_MAPPING.get(lift_type, "snatch")

    session = get_db_connection()
    try:
        resolved_user_id = _resolve_user_id(session, user_id, email)
        attempt_id, user_competition_id = _create_attempt_record(
            session, resolved_user_id, competition_id, database_lift_type, weight, public_url
        )
        logger.info(f"Finalize succeeded: attempt={attempt_id}, user={resolved_user_id}")
        return jsonify({
            'message': 'Upload finalized and attempt created',
            'url': public_url,
            'attempt_id': attempt_id,
            'user_competition_id': user_competition_id,
            'user_id': str(resolved_user_id),
        }), 200
    except Exception as e:
        session.rollback()
        error_details = traceback.format_exc()
        logger.error(f"Finalize error: {str(e)}")
        logger.error(error_details)
        return jsonify({'error': str(e)}), 500
    finally:
        session.close() 