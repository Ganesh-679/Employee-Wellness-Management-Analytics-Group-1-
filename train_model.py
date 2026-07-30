import os
import pickle
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report

def generate_synthetic_data(num_samples=10000):
    np.random.seed(42)
    
    # Generate features
    bmi = np.clip(np.random.normal(26.5, 5.0, num_samples), 15.0, 50.0)
    sleep_hours = np.clip(np.random.normal(7.0, 1.2, num_samples), 3.0, 12.0)
    exercise_minutes = np.clip(np.random.normal(130, 75, num_samples), 0, 600)
    bp_systolic = np.clip(np.random.normal(122, 12, num_samples), 90, 180).astype(int)
    bp_diastolic = np.clip(np.random.normal(80, 8, num_samples), 60, 110).astype(int)
    stress_level_encoded = np.random.choice([0, 1, 2], size=num_samples, p=[0.4, 0.4, 0.2])
    
    # Calculate score to determine the class labels
    base_scores = np.zeros(num_samples)
    
    # BMI points
    base_scores[bmi < 16.0] += 30           # severely underweight
    base_scores[(bmi >= 16.0) & (bmi < 18.5)] += 18   # underweight
    base_scores[bmi >= 30] += 25            # obese
    base_scores[(bmi >= 25) & (bmi < 30)] += 15       # overweight
    
    # Sleep points
    base_scores[sleep_hours < 5] += 20
    base_scores[(sleep_hours >= 5) & (sleep_hours < 7)] += 10
    
    # Exercise points
    base_scores[exercise_minutes < 150] += 10
    
    # Stress points
    base_scores[stress_level_encoded == 2] += 20  # High
    base_scores[stress_level_encoded == 1] += 10  # Medium
    
    # Blood Pressure points
    bp_high = (bp_systolic >= 140) | (bp_diastolic >= 90)
    bp_med = ((bp_systolic >= 130) | (bp_diastolic >= 85)) & ~bp_high
    base_scores[bp_high] += 20
    base_scores[bp_med] += 10
    
    # Add random noise (e.g., -5 to +5 points)
    noise = np.random.randint(-5, 6, size=num_samples)
    final_scores = np.clip(base_scores + noise, 0, 85)
    
    # Class labels
    risk_level = []
    for s in final_scores:
        if s >= 60:
            risk_level.append("High")
        elif s >= 30:
            risk_level.append("Medium")
        else:
            risk_level.append("Low")
            
    df = pd.DataFrame({
        "bmi": bmi,
        "sleep_hours": sleep_hours,
        "exercise_minutes_per_week": exercise_minutes,
        "bp_systolic": bp_systolic,
        "bp_diastolic": bp_diastolic,
        "stress_level_encoded": stress_level_encoded,
        "risk_level": risk_level
    })
    
    return df

def main():
    print("Generating synthetic health records...")
    df = generate_synthetic_data(10000)
    
    X = df.drop(columns=["risk_level"])
    y = df["risk_level"]
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    print("Scaling features...")
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    print("Training Random Forest Classifier (Optimized 30 estimators for instant inference)...")
    model = RandomForestClassifier(n_estimators=30, max_depth=10, random_state=42, n_jobs=-1)
    model.fit(X_train_scaled, y_train)
    
    y_pred = model.predict(X_test_scaled)
    acc = accuracy_score(y_test, y_pred)
    print(f"\nModel Accuracy: {acc:.4f}")
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred))
    
    # Save the model and scaler to the current directory
    model_path = "wellness_model.pkl"
    scaler_path = "scaler.pkl"
    
    print(f"Saving model to {model_path}...")
    with open(model_path, "wb") as f:
        pickle.dump(model, f)
        
    print(f"Saving scaler to {scaler_path}...")
    with open(scaler_path, "wb") as f:
        pickle.dump(scaler, f)
        
    print("Training complete! Model assets successfully saved.")

if __name__ == "__main__":
    main()
