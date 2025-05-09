import cv2
from pyzbar.pyzbar import decode
import numpy as np
import json

def scan_qr_code():
    cap = cv2.VideoCapture(0)

    while True:
        ret, frame = cap.read()

        if not ret:
            continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        decoded_objects = decode(gray)

        for obj in decoded_objects:
            data = obj.data.decode('utf-8')

            json_start = data.find('{')
            json_end = data.rfind('}') + 1
            valid_json_str = data[json_start:json_end]

            if valid_json_str:
                decoded_data = json.loads(valid_json_str)
                print("Solomon QR Code Data:", decoded_data)

                # Draw a rectangle around the QR code
                points = obj.polygon
                if len(points) > 4:
                    hull = cv2.convexHull(np.array([point for point in points], dtype=np.float32))
                    hull = list(map(tuple, np.squeeze(hull)))
                else:
                    hull = points

                n = len(hull)
                for j in range(0, n):
                    cv2.line(frame, hull[j], hull[(j + 1) % n], (255, 0, 0), 3)
            else:
                print("Normal QR Code Data:", data)
                points = obj.polygon
                if len(points) > 4:
                    hull = cv2.convexHull(np.array([point for point in points], dtype=np.float32))
                    hull = list(map(tuple, np.squeeze(hull)))
                else:
                    hull = points

                n = len(hull)
                for j in range(0, n):
                    cv2.line(frame, hull[j], hull[(j + 1) % n], (255, 0, 0), 3)

        cv2.imshow("QR Code Scanner", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    scan_qr_code()
