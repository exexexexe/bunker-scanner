# The deployed service only serves the pre-built static site. The processing
# pipeline (rasterio, GDAL, scipy) runs locally and is deliberately not in this
# image — building the site needs ~100 MB terrain tiles and has no business in a
# web dyno.
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py ./
COPY site ./site

ENV PORT=8000
EXPOSE 8000
CMD ["python", "server.py"]
