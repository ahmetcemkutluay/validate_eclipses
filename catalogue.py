from pathlib import Path
import pandas as pd

missing_val = -1

def load_catalogue(csv_path):
    """ read light curve results file to obtain star list"""

    path = Path(csv_path)

    if not path.exists():
        raise FileNotFoundError(f'CSV could not be found at {path}')

    return pd.read_csv(path, dtype={'tic': str})

def format_value(value, err=None, decimals = 4):
    """ -1 and NaN values are going to be shown as '--' , if there are errors show those too."""
    if isinstance(value, str):
        return value

    if pd.isna(value) or value == missing_val:
        return "--"

    if decimals == 0:
        text = f"{int(value)}"
    else:
        text = f"{float(value):.{decimals}f}"

    if err is not None and not pd.isna(err) and err != missing_val:
        text += f" \u00b1 {float(err):.{decimals}f}"

    return text
        
        

if __name__ == "__main__":
    import sys


    df = load_catalogue(sys.argv[1])
    print("Test sample: (row,col): ", df.shape)
    print("cols: ", list(df.columns))
    print()
    print(df.head(3))