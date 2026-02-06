# MistakeReservoir (错题池)

A local web-based application for managing exam mistakes, analyzing invalid questions, and generating customized practice papers.

## Features

- **Upload & Analyze**: Upload DOCX exam papers; the system automatically extracts questions, types, and materials.
- **Question Bank**: Efficiently store and browse questions with support for rich text and images.
- **Preview & Edit**: Verify extracted questions before saving them to the database. Edit content, options, and answers directly.
- **Exam Generation**: Randomly generate new "Mistake Papers" (DOCX) based on your accumulated wrong answers.
- **Statistics**: Track your upload activity and accuracy trends with heatmaps and charts.
- **Headless Mode**: Runs as a background service with a web interface. Automatically shuts down when the browser is closed.

## Installation

1.  Clone or download the repository.
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

### Running Locally

```bash
python main.py
```
This will automatically open your default browser to `http://127.0.0.1:8000`.

### Building an Executable

To create a standalone `.exe` file:

```bat
package.bat
```
The output file will be in the `dist/` folder.

## Project Structure

- `main.py`: FastAPI backend entry point.
- `database.py`: SQLite database manager.
- `extractor.py`: Logic for parsing DOCX files.
- `generator.py`: Logic for generating new DOCX papers.
- `parsing/`: Core parsing logic modules.
- `static/`: Frontend assets (HTML, CSS, JS).
- `media/`: Storage for extracted images (ignored in git).
- `uploads/`: Temporary storage for uploaded files (ignored in git).

## License

Personal Use Only.
