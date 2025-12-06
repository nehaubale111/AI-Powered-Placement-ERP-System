import pandas as pd
df = pd.read_csv("C:\\Users\\joshi\\OneDrive\\Desktop\\AI Powered Placement ERP\\jobs.csv")
print(df.columns.tolist())
df = pd.read_csv("C:\\Users\\joshi\\OneDrive\\Desktop\\AI Powered Placement ERP\\jobs.csv")
df.columns = df.columns.str.strip()   # remove spaces
print(f"\nCSV: {("C:\\Users\\joshi\\OneDrive\\Desktop\\AI Powered Placement ERP\\jobs.csv")}")
print("Headers:", df.columns.tolist())
print("First 5 rows:\n", df.head())
df = pd.read_csv("C:\\Users\\joshi\\OneDrive\\Desktop\\AI Powered Placement ERP\\applications.csv")
df.columns = df.columns.str.strip()   # remove spaces
print(f"\nCSV: {("C:\\Users\\joshi\\OneDrive\\Desktop\\AI Powered Placement ERP\\applications.csv")}")
print("Headers:", df.columns.tolist())
print("First 5 rows:\n", df.head())