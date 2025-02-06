# Use the official Python 3.9 image as a base image
FROM python:3.9-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install system dependencies (such as ffmpeg for discord.py)
RUN apt-get update && apt-get install -y ffmpeg

# Install pip requirements
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Make sure dotenv is loaded from environment variables
RUN pip install python-dotenv

# Expose the bot on port 8080 (or any port you prefer)
EXPOSE 8080

# Run the Python script when the container starts
CMD ["python", "bot.py"]
