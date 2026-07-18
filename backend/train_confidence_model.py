import sys
import os

# Align python path
sys.path.append(os.path.join(os.path.dirname(__file__), "app"))
sys.path.append(os.path.dirname(__file__))

from app.engine.confidence_model import train_and_save_model

if __name__ == "__main__":
    print("Initializing confidence model training session...")
    success = train_and_save_model()
    if success:
        print("Model training completed successfully and saved to app/data/confidence_model.pkl.")
        sys.exit(0)
    else:
        print("Model training failed. Please check backend logs.")
        sys.exit(1)
