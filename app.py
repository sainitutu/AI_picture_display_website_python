from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify
import sqlite3
import os
from datetime import datetime
from PIL import Image
import io
import struct
import json

app = Flask(__name__)

# Configuration
DB_PATH = 'database/aishow.db'
UPLOAD_PATH = 'assets/uploads'
THUMBNAIL_PATH = 'assets/thumbnails'
STATIC_PATH = 'public'

# Ensure directories exist
for path in [os.path.dirname(DB_PATH), UPLOAD_PATH, THUMBNAIL_PATH]:
    os.makedirs(path, exist_ok=True)

def get_db():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    return db

def init_db():
    with open('database/schema.sql', 'r', encoding='utf-8') as f:
        get_db().executescript(f.read())

# Initialize database if it doesn't exist
if not os.path.exists(DB_PATH):
    init_db()

def create_thumbnail(image_path):
    with Image.open(image_path) as img:
        img.thumbnail((200, 200))
        thumbnail_path = os.path.join(THUMBNAIL_PATH, os.path.basename(image_path))
        img.save(thumbnail_path)
        return thumbnail_path

def get_image_keywords(db, image_id):
    keywords = db.execute('''
        SELECT GROUP_CONCAT(k.keyword) as keywords
        FROM keywords k
        JOIN image_keywords ik ON k.id = ik.keyword_id
        WHERE ik.image_id = ?
        GROUP BY ik.image_id
    ''', [image_id]).fetchone()
    
    if keywords and keywords['keywords']:
        return keywords['keywords'].split(',')
    return []

def save_keywords(db, image_id, keywords_str):
    if not keywords_str:
        return
        
    keywords = [k.strip() for k in keywords_str.split(',') if k.strip()]
    if not keywords:
        return
        
    # Delete existing keywords for this image
    db.execute('DELETE FROM image_keywords WHERE image_id = ?', [image_id])
    
    # Add new keywords
    for keyword in keywords:
        # Get or create keyword
        result = db.execute('SELECT id FROM keywords WHERE keyword = ?', [keyword]).fetchone()
        if result:
            keyword_id = result[0]
        else:
            cursor = db.execute('INSERT INTO keywords (keyword) VALUES (?)', [keyword])
            keyword_id = cursor.lastrowid
        
        # Link keyword to image
        db.execute(
            'INSERT INTO image_keywords (image_id, keyword_id) VALUES (?, ?)',
            [image_id, keyword_id]
        )

def analyze_png_metadata(file_path):
    try:
        app.logger.info(f"Analyzing image: {file_path}")
        
        # Try reading PNG chunks
        with open(file_path, 'rb') as f:
            # Verify PNG signature
            signature = f.read(8)
            if signature != b'\x89PNG\r\n\x1a\n':
                return {'found': False, 'data': None}
            
            while True:
                try:
                    # Read chunk length
                    length_data = f.read(4)
                    if not length_data:
                        break
                    length = struct.unpack('>I', length_data)[0]
                    
                    # Read chunk type
                    chunk_type = f.read(4).decode('ascii')
                    
                    # Read chunk data
                    data = f.read(length)
                    
                    # Skip CRC
                    f.read(4)
                    
                    # Check for tEXt chunk
                    if chunk_type == 'tEXt':
                        try:
                            null_index = data.index(b'\0')
                            keyword = data[:null_index].decode('latin-1')
                            content = data[null_index + 1:].decode('latin-1')
                            
                            app.logger.info(f"Found PNG text chunk: {keyword}")
                            
                            # Check for workflow (Comfy)
                            if keyword == 'workflow':
                                app.logger.info("Found workflow field")
                                return {'found': True, 'data': {'workflow': content}}
                            
                            # Check for parameters (SD)
                            if keyword == 'parameters' or (
                                'Steps:' in content and 
                                'Negative prompt:' in content
                            ):
                                app.logger.info("Found SD parameters")
                                return {'found': True, 'data': {'parameters': content}}
                            
                            # Check for prompt (might contain parameters)
                            if keyword == 'prompt' and (
                                'Steps:' in content or 
                                'Negative prompt:' in content
                            ):
                                app.logger.info("Found SD parameters in prompt")
                                return {'found': True, 'data': {'parameters': content}}
                            
                        except ValueError:
                            continue
                    
                except Exception as e:
                    app.logger.error(f"Error reading PNG chunk: {str(e)}")
                    break
        
        # Try reading metadata from PIL
        try:
            with Image.open(file_path) as img:
                if 'parameters' in img.info:
                    app.logger.info("Found parameters in PIL metadata")
                    return {'found': True, 'data': {'parameters': img.info['parameters']}}
                if 'workflow' in img.info:
                    app.logger.info("Found workflow in PIL metadata")
                    return {'found': True, 'data': {'workflow': img.info['workflow']}}
                if 'Comment' in img.info:
                    comment = img.info['Comment']
                    if 'Steps:' in comment and 'Negative prompt:' in comment:
                        app.logger.info("Found SD parameters in Comment")
                        return {'found': True, 'data': {'parameters': comment}}
                    try:
                        comment_data = json.loads(comment)
                        if 'workflow' in comment_data:
                            app.logger.info("Found workflow in Comment JSON")
                            return {'found': True, 'data': {'workflow': json.dumps(comment_data['workflow'], indent=2)}}
                    except:
                        pass
        except Exception as e:
            app.logger.error(f"Error reading PIL metadata: {str(e)}")
        
        app.logger.info("No metadata found in image")
        return {'found': False, 'data': None}
        
    except Exception as e:
        app.logger.error(f'Image analysis error: {str(e)}')
        return {'found': False, 'error': f'圖片分析失敗: {str(e)}'}

@app.route('/api/analyze_keywords', methods=['POST'])
def analyze_keywords():
    try:
        data = request.get_json()
        prompt = data.get('prompt', '').strip() if data else ''

        if not prompt:
            return jsonify({'error': '提詞不能為空'})

        # Get database connection
        db = get_db()
        
        # Get all keywords from database
        keywords = db.execute('SELECT keyword FROM keywords').fetchall()
        db_keywords = [row['keyword'] for row in keywords]
        
        # Split prompt into parts
        prompt_parts = [part.strip() for part in prompt.split(',')]
        
        # Find matches
        matches = []
        for part in prompt_parts:
            for keyword in db_keywords:
                if keyword.lower() in part.lower():
                    matches.append(keyword)
        
        # Remove duplicates while preserving order
        matches = list(dict.fromkeys(matches))
        
        return jsonify({
            'success': True,
            'keywords': matches
        })

    except Exception as e:
        app.logger.error('Analyze keywords error: ' + str(e))
        return jsonify({
            'error': '分析關鍵詞失敗: ' + str(e)
        })

@app.route('/api/analyze', methods=['POST'])
def analyze_image():
    if 'image' not in request.files:
        return jsonify({'found': False, 'error': '無效的請求'})
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({'found': False, 'error': '無效的請求'})
    
    # Save the file temporarily
    temp_path = os.path.join(UPLOAD_PATH, 'temp_' + file.filename)
    try:
        file.save(temp_path)
        result = analyze_png_metadata(temp_path)
        return jsonify(result)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

@app.route('/')
def index():
    keywords = request.args.get('keywords', '').split(',') if request.args.get('keywords') else []
    image_visibility = request.args.get('visibility', 'hide_restricted')
    image_type = request.args.get('type')

    db = get_db()
    query = '''
        SELECT i.* 
        FROM images i 
    '''
    
    conditions = []
    params = []

    if image_visibility == 'hide_restricted':
        conditions.append('i.is_hidden = 0')
    elif image_visibility == 'only_restricted':
        conditions.append('i.is_hidden = 1')

    if image_type:
        conditions.append('i.type = ?')
        params.append(image_type)

    if keywords:
        keyword_conditions = []
        for keyword in keywords:
            keyword_conditions.append('EXISTS (SELECT 1 FROM image_keywords ik JOIN keywords k ON ik.keyword_id = k.id WHERE ik.image_id = i.id AND k.keyword = ?)')
            params.append(keyword.strip())
        if keyword_conditions:
            conditions.append(f"({' OR '.join(keyword_conditions)})")

    if conditions:
        query += ' WHERE ' + ' AND '.join(conditions)

    query += ' ORDER BY i.created_at DESC'
    
    images = db.execute(query, params).fetchall()
    
    # Get keywords for each image
    result_images = []
    for image in images:
        image_dict = dict(image)
        image_dict['keywords'] = ','.join(get_image_keywords(db, image['id']))
        result_images.append(image_dict)
    
    return render_template('index.html', images=result_images)

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        if 'image' not in request.files:
            return redirect(request.url)
        
        file = request.files['image']
        if file.filename == '':
            return redirect(request.url)

        if file:
            filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
            file_path = os.path.join(UPLOAD_PATH, filename)
            file.save(file_path)
            
            create_thumbnail(file_path)
            
            db = get_db()
            cursor = db.cursor()
            
            # Get form data
            image_type = request.form.get('type', 'SD')
            details = request.form.get('details', '')
            is_hidden = 1 if request.form.get('is_hidden') else 0
            
            cursor.execute(
                'INSERT INTO images (image_path, type, details, is_hidden) VALUES (?, ?, ?, ?)',
                (filename, image_type, details, is_hidden)
            )
            image_id = cursor.lastrowid
            
            # Save keywords
            keywords = request.form.get('keywords', '')
            save_keywords(db, image_id, keywords)
            
            db.commit()
            
            return redirect(url_for('index'))
    
    return render_template('upload.html')

@app.route('/view/<int:image_id>')
def view_image(image_id):
    db = get_db()
    image = db.execute('SELECT * FROM images WHERE id = ?', [image_id]).fetchone()
    
    if image is None:
        return redirect(url_for('index'))
    
    # Get keywords
    image_dict = dict(image)
    image_dict['keywords'] = ','.join(get_image_keywords(db, image_id))
    
    return render_template('view.html', image=image_dict)

@app.route('/edit/<int:image_id>', methods=['GET', 'POST'])
def edit_image(image_id):
    db = get_db()
    
    if request.method == 'POST':
        if 'delete' in request.form:
            # Delete image
            image = db.execute('SELECT image_path FROM images WHERE id = ?', [image_id]).fetchone()
            if image:
                # Delete files
                try:
                    file_path = os.path.join(UPLOAD_PATH, image['image_path'])
                    thumb_path = os.path.join(THUMBNAIL_PATH, image['image_path'])
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    if os.path.exists(thumb_path):
                        os.remove(thumb_path)
                except Exception as e:
                    app.logger.error(f"Error deleting files: {str(e)}")
                
                # Delete from database
                db.execute('DELETE FROM image_keywords WHERE image_id = ?', [image_id])
                db.execute('DELETE FROM images WHERE id = ?', [image_id])
                db.commit()
            
            return redirect(url_for('index'))
        
        elif 'save' in request.form:
            # Update image
            type_ = request.form.get('type')
            details = request.form.get('details')
            is_hidden = 1 if request.form.get('is_hidden') else 0
            
            db.execute(
                'UPDATE images SET type = ?, details = ?, is_hidden = ? WHERE id = ?',
                [type_, details, is_hidden, image_id]
            )
            
            # Save keywords
            keywords = request.form.get('keywords', '')
            save_keywords(db, image_id, keywords)
            
            db.commit()
            return redirect(url_for('view_image', image_id=image_id))
    
    image = db.execute('SELECT * FROM images WHERE id = ?', [image_id]).fetchone()
    
    if image is None:
        return redirect(url_for('index'))
    
    # Get keywords
    image_dict = dict(image)
    image_dict['keywords'] = ','.join(get_image_keywords(db, image_id))
    
    return render_template('edit.html', image=image_dict)

@app.route('/api/suggest')
def suggest_keywords():
    partial = request.args.get('q', '').strip()
    if not partial:
        return jsonify([])

    db = get_db()
    suggestions = db.execute('''
        SELECT DISTINCT keyword 
        FROM keywords 
        WHERE keyword LIKE ? 
        ORDER BY keyword 
        LIMIT 10
    ''', [f'%{partial}%']).fetchall()
    
    return jsonify([s['keyword'] for s in suggestions])

@app.route('/api/keyword', methods=['POST'])
def add_keyword():
    data = request.get_json()
    keyword = data.get('keyword', '').strip()
    
    if not keyword:
        return jsonify({'error': '關鍵詞不能為空'}), 400
    
    db = get_db()
    try:
        db.execute('INSERT INTO keywords (keyword) VALUES (?)', [keyword])
        db.commit()
        return jsonify({'success': True})
    except sqlite3.IntegrityError:
        return jsonify({'success': True})  # Keyword already exists
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/cleanup', methods=['POST'])
def cleanup():
    try:
        # Get all image paths from database
        db = get_db()
        db_images = db.execute('SELECT image_path FROM images').fetchall()
        db_image_paths = set(img['image_path'] for img in db_images)
        
        # Get all files in uploads and thumbnails directories
        upload_files = set(f for f in os.listdir(UPLOAD_PATH) if f != '.gitkeep' and not f.startswith('temp_'))
        thumbnail_files = set(f for f in os.listdir(THUMBNAIL_PATH) if f != '.gitkeep')
        
        # Remove files not in database
        removed_count = 0
        for file in upload_files:
            if file not in db_image_paths:
                file_path = os.path.join(UPLOAD_PATH, file)
                if os.path.exists(file_path):
                    os.remove(file_path)
                    removed_count += 1
                
        for file in thumbnail_files:
            if file not in db_image_paths:
                file_path = os.path.join(THUMBNAIL_PATH, file)
                if os.path.exists(file_path):
                    os.remove(file_path)
                    removed_count += 1
        
        return jsonify({
            'success': True,
            'message': f'已清理 {removed_count} 個未使用的檔案'
        })
    except Exception as e:
        app.logger.error(f"Cleanup error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/css/<path:filename>')
def serve_css(filename):
    return send_from_directory(os.path.join(STATIC_PATH, 'css'), filename)

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_PATH, filename)

@app.route('/thumbnails/<path:filename>')
def thumbnail_file(filename):
    return send_from_directory(THUMBNAIL_PATH, filename)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
