import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

df = pd.read_csv('data/transaction.csv')
print(df.head())

# 3. Define the Categorization Logic
def categorize(merchant):
    # Convert merchant to lowercase to ensure case-insensitive matching
    merchant = str(merchant).lower()
    
    if "zomato" in merchant or "swiggy" in merchant or "starbucks" in merchant or "dominoz" in merchant:
        return "Food & Dining"
    elif "uber" in merchant or "ola" in merchant or "petrol" in merchant:
        return "Travel & Transport"
    elif "netflix" in merchant or "spotify" in merchant or "bookmyshow" in merchant:
        return "Entertainment"
    elif "blinkit" in merchant or "kirana" in merchant:
        return "Groceries"
    elif "airtel" in merchant:
        return "Bills & Utilities"
    elif "myntra" in merchant or "h&m" in merchant or "amazon" in merchant or "flipkart" in merchant:
        return "Shopping"
    elif "gym" in merchant:
        return "Health & Fitness"
    else:
        return "Others"

# 4. Apply the function to create a new 'Category' column
df['Category'] = df['Merchant Name'].apply(categorize)

# 5. Display the results to verify
print("Categorized Transactions:")
print(df[['Date', 'Merchant Name', 'Category', 'Amount']].head(10))

# 6. Spending summary
print("\n--- Spending Summary ---")

summary = df.groupby("Category")["Amount"].sum()
for category, total in summary.items():
    print(f"{category} : {total}")



# 6. Feature 5 — Visualization
print("\n--- Generating Spending Charts ---")

# Ensure the output directory exists so the code doesn't crash
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
output_dir = os.path.join(BASE_DIR, 'output')
os.makedirs(output_dir, exist_ok=True)

# Clean up our summary data for plotting
# summary.index gives the Category names (X-axis)
# summary.values gives the Total Amounts (Y-axis)
categories = summary.index
amounts = summary.values

# Create a figure canvas (Width: 10 inches, Height: 6 inches)
plt.figure(figsize=(10, 6))

# Create a bar chart with custom colors
plt.bar(categories, amounts, color='skyblue', edgecolor='black')

# Add titles and labels to make it readable
plt.title('Total Spending by Category', fontsize=16, fontweight='bold')
plt.xlabel('Category', fontsize=12)
plt.ylabel('Amount Spent (₹)', fontsize=12)

# Rotate the X-axis category text slightly so long names don't overlap
plt.xticks(rotation=15)

# Add a clean grid along the Y-axis behind the bars
plt.grid(axis='y', linestyle='--', alpha=0.7)

# Adjust layout automatically so nothing gets cut off
plt.tight_layout()

# Save the plot image directly to your output folder
chart_path = os.path.join(output_dir, 'spending_summary.png')
plt.savefig(chart_path)
print(f"Success! Bar chart saved to: {chart_path}")

# Optional: If you want to view it pop up on your screen right away
# plt.show()