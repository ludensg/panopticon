# Use an official slim Python image with working venv/pip
FROM python:3.11-slim

# Set working directory inside the container
WORKDIR /app

# Install any OS-level deps you might need (minimal)
# Add more apt packages here if some Python libs complain
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
 && rm -rf /var/lib/apt/lists/*

# Copy only requirements first (so Docker can cache pip layer)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Now copy the rest of the app
COPY . .

# Default Streamlit port
ENV STREAMLIT_PORT=8501

# Streamlit needs to listen on 0.0.0.0 inside container
EXPOSE 8501

# Optional: allow choosing backend via env var (OPENAI / OLLAMA), if your app supports it
# ENV PANOPTICON_BACKEND=openai

# Entrypoint: run the Streamlit app
CMD ["sh", "-c", "streamlit run app.py --server.port=${STREAMLIT_PORT} --server.address=0.0.0.0"]
