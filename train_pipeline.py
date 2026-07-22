import os
import subprocess
import sys

def main():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(root_dir)
    print("Project Root:", root_dir)

    # 1. Run simulator for 'normal' scenario
    print("\n--- Step 1: Running normal scenario simulation ---")
    sim_script = os.path.join("digital twin", "simulate.py")
    output_dir = os.path.join("data", "raw", "normal")
    
    cmd_sim = [
        sys.executable,
        sim_script,
        "--scenario", "normal",
        "--duration", "5000",
        "--format", "csv",
        "--output", output_dir,
        "--quiet"
    ]
    print("Running:", " ".join(cmd_sim))
    subprocess.run(cmd_sim, check=True)
    print("Simulation completed.")

    # 2. Extract features via batch_processor
    print("\n--- Step 2: Extracting features from simulation data ---")
    # We run batch_processor as a python module with PYTHONPATH set to the current directory
    env = os.environ.copy()
    env["PYTHONPATH"] = root_dir + os.pathsep + env.get("PYTHONPATH", "")
    
    cmd_batch = [
        sys.executable,
        "-m", "backend.app.ai.evaluation.batch_processor"
    ]
    print("Running:", " ".join(cmd_batch))
    subprocess.run(cmd_batch, env=env, check=True)
    print("Feature extraction completed.")

    # 3. Train anomaly detector
    print("\n--- Step 3: Training anomaly detector ---")
    model_output_dir = os.path.join("backend", "app", "models", "anomaly_detector")
    os.makedirs(model_output_dir, exist_ok=True)
    
    cmd_train = [
        sys.executable,
        "-m", "backend.app.ai.training.train_anomaly",
        "--input", os.path.join("data", "processed", "normal_features.parquet"),
        "--config", os.path.join("backend", "app", "ai", "config", "anomaly_model.yaml"),
        "--output", model_output_dir
    ]
    print("Running:", " ".join(cmd_train))
    subprocess.run(cmd_train, env=env, check=True)
    print("Training pipeline finished successfully!")

if __name__ == "__main__":
    main()
