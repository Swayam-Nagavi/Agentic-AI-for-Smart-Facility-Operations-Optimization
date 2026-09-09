from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import balanced_accuracy_score, classification_report
from sklearn.model_selection import train_test_split


DATA_DIR = Path("data/lbnl")
MODEL_DIR = Path("models")
MODEL_PATH = MODEL_DIR / "maintenance_fault_model.joblib"

RANDOM_STATE = 42
TRAIN_PER_FILE = 10000
TEST_PER_FILE = 1000


def load_labeled_data():
    files = sorted(DATA_DIR.rglob("*.csv"))

    if not files:
        raise FileNotFoundError(
            f"No LBNL CSV files found under '{DATA_DIR}'."
        )

    train_parts = []
    test_parts = []

    for path in files:
        df = pd.read_csv(path)

        if df.empty:
            continue

        numeric_columns = []

        for column in df.columns:
            converted = pd.to_numeric(df[column], errors="coerce")

            if converted.notna().sum() >= int(len(df) * 0.50):
                numeric_columns.append(column)

        numeric_columns = [
            column for column in numeric_columns
            if column != "Datetime"
        ]

        if not numeric_columns:
            continue

        data = df[numeric_columns].apply(
            pd.to_numeric,
            errors="coerce",
        )

        data = data.replace([float("inf"), float("-inf")], pd.NA)
        data = data.dropna()

        if len(data) < 100:
            continue

        # LBNL baseline file is fault-free.
        # Every other downloaded case represents a fault condition.
        label = 0 if path.stem == "RTU_sim_baseline" else 1

        data["fault"] = label

        split_index = int(len(data) * 0.80)

        train_data = data.iloc[:split_index]
        test_data = data.iloc[split_index:]

        train_sample_size = min(TRAIN_PER_FILE, len(train_data))
        test_sample_size = min(TEST_PER_FILE, len(test_data))

        train_parts.append(
            train_data.sample(
                n=train_sample_size,
                random_state=RANDOM_STATE,
            )
        )

        test_parts.append(
            test_data.sample(
                n=test_sample_size,
                random_state=RANDOM_STATE,
            )
        )

    if not train_parts or not test_parts:
        raise ValueError("Unable to create training and testing data.")

    train = pd.concat(train_parts, ignore_index=True)
    test = pd.concat(test_parts, ignore_index=True)

    return train, test


def train_model():
    train, test = load_labeled_data()

    X_train = train.drop(columns=["fault"])
    y_train = train["fault"]

    X_test = test.drop(columns=["fault"])
    y_test = test["fault"]

    model = RandomForestClassifier(
        n_estimators=80,
        max_depth=16,
        class_weight="balanced",
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )

    model.fit(X_train, y_train)

    predictions = model.predict(X_test)

    accuracy = balanced_accuracy_score(
        y_test,
        predictions,
    )

    print(f"Training samples: {len(X_train):,}")
    print(f"Testing samples:  {len(X_test):,}")
    print(f"Balanced accuracy: {accuracy * 100:.2f}%")
    print()
    print(classification_report(y_test, predictions))

    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    joblib.dump(model, MODEL_PATH)

    print(f"Model saved to: {MODEL_PATH}")


if __name__ == "__main__":
    train_model()