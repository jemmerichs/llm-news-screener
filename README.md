# TwitchBot Project

## Running the Server and UI

### 1. Install Dependencies

Make sure you have Python 3.8+ and `pip` installed.
Install all required packages:
```bash
pip install -r requirements.txt
```

### 2. Set Up Environment Variables

Ensure your `.env` file is in the project root and contains all required keys (e.g., `ANTHROPIC_API_KEY`, Reddit credentials, etc.).

### 3. Start the FastAPI Server

The backend server (including API and static UI) is served via FastAPI.
Run this command from the project root:
```bash
uvicorn src.web_server:app --reload
```
- The `--reload` flag enables auto-reloading for development.
- By default, the server will be available at [http://127.0.0.1:8000/](http://127.0.0.1:8000/).

### 4. Access the UI

Open your browser and go to:
```
http://127.0.0.1:8000/
```
- This will serve the `static/index.html` file as the main UI.
- All static assets (JS, CSS) are available under `/static/`.

### 5. Running the Main Bot Logic (Optional/Advanced)

If you want to run the main event/news processing loop (not required for just the UI/API), use:
```bash
python -m src.main
```
- This runs the background bot logic (news scraping, event prediction, etc.).
- Make sure your `.env` is set up before running this. 