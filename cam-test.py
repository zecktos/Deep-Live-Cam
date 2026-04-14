import cv2

def find_cameras(max_tested=10):
    available = []
    for i in range(max_tested):
        cap = cv2.VideoCapture(i)
        if cap is not None and cap.isOpened():
            available.append(i)
            cap.release()
    return available

# Find cameras
cameras = find_cameras()

print("Available cameras:", cameras)

if not cameras:
    print("No cameras found.")
    exit()

# Use the last available camera
cam_index = cameras[5]
cap = cv2.VideoCapture(cam_index, cv2.CAP_DSHOW)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 800)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 600)

print(f"Opening camera {cam_index}...")

while True:
    ret, frame = cap.read()
    #print(cap.get(3))
    #print(cap.get(4))
    if not ret:
        print("Failed to grab frame")
        break

    cv2.imshow("Camera Feed", frame)

    # Press 'q' to quit
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()