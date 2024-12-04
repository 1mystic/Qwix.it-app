Qwix.it, is a multi-user household service app.

Setting Up the Development Environment
Requirements:

Python 3.x (https://www.python.org/downloads/)
pip (package installer for Python) - usually comes bundled with Python installation.
Instructions:

Download the Code:

Clone the repository using Git:

Bash
git clone https://<your_repository_url>.git
Use code with caution.

Or, download the repository as a ZIP file:

Go to the project's repository on your preferred platform (e.g., GitHub).
Click on "Code" and then "Download ZIP".
Create a Virtual Environment (Recommended):

A virtual environment helps isolate project dependencies and avoid conflicts with other Python projects on your system.

Bash
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate.bat  # Windows
Use code with caution.

Install Dependencies:

Activate your virtual environment (if you created one).

Bash
pip install -r requirements.txt
Use code with caution.

This will install all the necessary Python libraries listed in the requirements.txt file.

Running the Application:

Start the Server:

Run the main script with:

Bash
python main.py
Use code with caution.

This will start the Flask development server.

Access the Application:

By default, the app runs on http://127.0.0.1:5000/. Open this URL in your web browser.
Note:

The port number (5000) might be different if another application is already using it. Check the console output for the actual port number assigned.
This is a development server. For production environments, a different server setup is recommended (e.g., Gunicorn with a web server like Nginx).
Additional Notes
This README assumes you have a basic understanding of Python development and the command line.
The requirements.txt file specifies the necessary dependencies for the project.
Feel free to explore the codebase and customize the application as needed.
