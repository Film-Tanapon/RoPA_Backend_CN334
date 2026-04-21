FROM python:3.10-slim
# อัปเดตและติดตั้ง Chromium (Chrome สําหรับ Linux) และตัว Driver
RUN apt-get update && apt-get install -y chromium chromium-driver
# กําหนดพื้นที่ทํางานภายใน Docker
WORKDIR /tests
# คัดลอกไฟล requirements และติดตั้ง
COPY requirements-test.txt .
RUN pip install --no-cache-dir -r requirements-test.txt
# กําหนดคําสั่งเริ่มตน: สั่งรัน robot และเก็บผลลัพธไวที่โฟลเดอร results
CMD ["robot", "-d", "results", "."]