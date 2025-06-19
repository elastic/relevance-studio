####  Build the UI  ############################################################

FROM node:20.15.1-slim AS ui
WORKDIR /app

# Copy project files
COPY package.json yarn.lock .babelrc webpack.config.js ./ 
COPY src/ui ./src/ui

# Install dependencies and build
RUN yarn install
RUN yarn build

####  Build the server  ########################################################

FROM python:3.10-slim AS server
WORKDIR /app

# Copy project files
COPY requirements.txt ./
COPY src/server ./server
COPY --from=ui /app/dist ./server/static

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

####  Run the server  ##########################################################

# Set environment variables
ENV FLASK_APP=server/flask.py
ENV FLASK_RUN_PORT=4096
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1
ENV STATIC_PATH=/app/server/static

# Run the server
CMD ["flask", "run", "--host=0.0.0.0"]
EXPOSE 4096