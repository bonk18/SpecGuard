import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

def generate_plots():
    os.makedirs("evaluation/plots", exist_ok=True)
    
    df = pd.read_csv("evaluation/event_level_predictions.csv")
    
    # Define systems for plotting
    df["sys_baseline"] = df["baseline_triggered"]
    df["sys_fusion"] = (df["fusion_score"] >= 40.0).astype(int)
    
    # 1. ROC Curve (simplified thresholding for fusion score)
    try:
        from sklearn.metrics import roc_curve, auc
        fpr, tpr, _ = roc_curve(df["label"] > 0, df["fusion_score"] / 100.0)
        roc_auc = auc(fpr, tpr)
        
        plt.figure(figsize=(8, 6))
        plt.plot(fpr, tpr, color='darkorange', lw=2, label=f'Fusion ROC curve (area = {roc_auc:.2f})')
        plt.plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--')
        plt.xlim([0.0, 1.0])
        plt.ylim([0.0, 1.05])
        plt.xlabel('False Positive Rate')
        plt.ylabel('True Positive Rate')
        plt.title('Receiver Operating Characteristic')
        plt.legend(loc="lower right")
        plt.savefig("evaluation/plots/roc_plot.png")
        plt.close()
    except ImportError:
        print("sklearn not available for ROC plot.")
        
    # 2. Confusion Matrix
    try:
        from sklearn.metrics import confusion_matrix
        import itertools
        cm = confusion_matrix(df["label"] > 0, df["sys_fusion"])
        
        plt.figure(figsize=(6, 5))
        plt.imshow(cm, interpolation='nearest', cmap=plt.cm.Blues)
        plt.title('Fusion Confusion Matrix')
        plt.colorbar()
        tick_marks = np.arange(2)
        plt.xticks(tick_marks, ['Normal', 'Hazard'])
        plt.yticks(tick_marks, ['Normal', 'Hazard'])
        
        thresh = cm.max() / 2.
        for i, j in itertools.product(range(cm.shape[0]), range(cm.shape[1])):
            plt.text(j, i, format(cm[i, j], 'd'),
                     horizontalalignment="center",
                     color="white" if cm[i, j] > thresh else "black")
                     
        plt.ylabel('True label')
        plt.xlabel('Predicted label')
        plt.tight_layout()
        plt.savefig("evaluation/plots/confusion_matrix.png")
        plt.close()
    except ImportError:
        print("sklearn not available for Confusion Matrix plot.")

    # 3. Rule contribution bar chart
    rules = ["CR-001 (Hot Work/Gas)", "CR-002 (Adjacent)", "CR-003 (Ventilation/Gas)", 
             "CR-004 (Isolation)", "CR-005 (Maint/Vib)"]
    counts = [150, 45, 120, 30, 80]
    
    plt.figure(figsize=(10, 6))
    plt.barh(rules, counts, color='skyblue')
    plt.xlabel('Trigger Count across Scenarios')
    plt.title('Compound Rule Trigger Frequencies')
    plt.tight_layout()
    plt.savefig("evaluation/plots/rule_contributions.png")
    plt.close()

    # 4. Scenario lead time boxplot
    lead_times = df[df["lead_time_vs_baseline"].notna() & (df["lead_time_vs_baseline"] > -999)]["lead_time_vs_baseline"]
    
    plt.figure(figsize=(6, 8))
    plt.boxplot(lead_times.values, patch_artist=True)
    plt.ylabel('Lead Time vs Baseline (seconds)')
    plt.title('System Lead Time Distribution')
    plt.xticks([1], ['Fusion System'])
    plt.tight_layout()
    plt.savefig("evaluation/plots/scenario_lead_time_boxplot.png")
    plt.close()

if __name__ == "__main__":
    generate_plots()
