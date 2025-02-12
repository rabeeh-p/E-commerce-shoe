FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory
WORKDIR /app

# Install system dependencies required for psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev gcc python3-dev

# Copy and install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Copy the application files
COPY . /app/
# COPY shoe_spectra/ /app/
ENV SECRET_KEY="django-insecure-v9zfx2ugz#h+y^m1i!p-=a3efyi55ra&&_1$i-83_so*t0@rpd"
ENV GOOGLE_CLIENT_ID="1026950511350-h4a1dik27uugqja7oe1qhstml3kc0hjh.apps.googleusercontent.com"
ENV GOOGLE_SECRET_KEY="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"

# Expose the Django port
EXPOSE 8000

# Collect static files
RUN python manage.py collectstatic --noinput 
# RUN python shoe_spectra/manage.py collectstatic --noinput

# Start the Django application
# CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "shoe_spectra.wsgi:application"]
