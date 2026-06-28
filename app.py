import os
from flask import Flask, request, jsonify, render_template # type: ignore
from werkzeug.utils import secure_filename # type: ignore

# Import the processing pipeline built inside your notebook environment
from pipeline_package import pipeline # type: ignore

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__, template_folder=os.path.join(BASE_DIR, "templates"), static_folder=os.path.join(BASE_DIR, "static"))

@app.route("/")
def index():
    return render_template("index.html")
@app.route("/rank", methods=["POST"])
def rank():
    # 1. Grab Job Description input
    jd_text = request.form.get("job_description", "").strip()
    jd_file = request.files.get("jd_file")
    
    # Grab dynamic shortlist top_k selection from user input (Default to 5 if empty)
    top_k = request.form.get("top_k", default=5, type=int)
    
    if not jd_text and jd_file and jd_file.filename:
        # If user uploaded a file instead of copying text, read its raw bytes
        jd_bytes = jd_file.read()
        jd_text = pipeline.extract_text_from_bytes(jd_bytes, jd_file.filename)

    if not jd_text:
        return jsonify({"error": "Missing job description context."}), 400

    # 2. Gather uploaded resumes
    uploaded_files = request.files.getlist("resumes")
    resumes_payload = []

    for f in uploaded_files:
        if f and f.filename:
            safe_name = secure_filename(f.filename)
            file_bytes = f.read()
            
            # Save a physical copy to the uploads directory for user downloading later
            f.seek(0)
            f.save(os.path.join(UPLOAD_DIR, safe_name))
            
            # Append payload dictionary with raw data
            resumes_payload.append({
                "bytes": file_bytes,
                "filename": safe_name
            })

    if not resumes_payload:
        return jsonify({"error": "Please upload at least one valid resume."}), 400

    # 3. Trigger your Notebook pipeline processing logic
    try:
        jd_data = {"text": jd_text}
        # Pass top_k option to the backend pipeline
        final_rankings = pipeline.process_and_rank(jd_data, resumes_payload, top_k=top_k)
        
        return jsonify({"results": final_rankings, "total": len(final_rankings)})
    except Exception as e:
        return jsonify({"error": f"Pipeline execution failed: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5000)