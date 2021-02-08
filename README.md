# Dependencies:

# Configure Aurora MySQL in AWS
# Add the details into settings.py under app >> app

# Run the below dependencies independently
Django==3.1.4
djangorestframework==3.12.2
psycopg2>=2.8.6,<2.9.6

flake8==3.8.4

# Or 

# Run dependencies from requirement.txt

COPY ./requirements.txt /requirements.txt

pip install -r /requirements.txt 

# Run the api in local

cd app

python .\manage.py runserver

# Update in the model

python .\manage.py makemigrations

python .\manage.py migrate

# Run in virtual environment in windows machine

Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process

.venv/Scripts/Activate.ps1
