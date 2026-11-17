""" read TESS LCs according to the pipeline given. The base code is taken from my other project called search_eclipses"""
""" The code works for SPOC, QLP, TGLC and T16 pipelines. I have not updated the code for reading LC from FFI images. 

This is something I also plan in 2027, to put some raw FFIs and centroid motion too. If you fancy contributing, feel free to write me.
"""
from pathlib import Path

import numpy as np
from astropy.io import fits

TIME_COLUMNS    = ['TIME', 'time', 'TMID_BJD']
FLUX_COLUMNS    = ['SAP_FLUX', 'cal_aper_flux', 'KSPSAP_FLUX', 'DET_FLUX', 'FLUX']
MAG_COLUMNS     = ['IRM3']            # since I use T16 light curves too. 
QUALITY_COLUMNS = ['QUALITY', 'TGLC_flags', 'TESS_flags']

def fits_files_for(lc_root, tic):
    """Read every available fits file for a given TIC"""
    folder = Path(lc_root) / f"tic_{tic}"
    if not folder.is_dir():
        return []
    return sorted(folder.rglob("*.fits"))

def read_lc(path):
    """One fits -> (time, normalized flux, pipeline, sector, fcol, tessmag)"""
    with fits.open(path) as hdul:
        h0, d = hdul[0].header, hdul[1].data
        cols = hdul[1].columns.names

        tcol = next((c for c in TIME_COLUMNS if c in cols), None)
        if tcol is None:
            raise ValueError(f"No time column in {Path(path).name}")

        fcol = next((c for c in FLUX_COLUMNS if c in cols), None)
        mcol = next((c for c in MAG_COLUMNS if c in cols), None) if fcol is None else None
        if fcol is None and mcol is None:
            raise ValueError(f"No flux or magnitude column in {Path(path).name}")

        t = np.asarray(d[tcol], dtype=float)
        y = np.asarray(d[fcol if fcol is not None else mcol], dtype=float)

        qcol = next((c for c in QUALITY_COLUMNS if c in cols), None)
        q = np.asarray(d[qcol], dtype=int) if qcol is not None else np.zeros(t.size, dtype=int)

        # time frames matter too.
        if t.size and np.nanmedian(t) > 2.4e6:
            t = t - 2457000.0

        good = np.isfinite(t) & np.isfinite(y) & (q == 0)
        if fcol is not None:
            good &= (y > 0)

        t, y = t[good], y[good]
        if t.size == 0:
            raise ValueError(f"No good points left in {Path(path).name}")

        if mcol is not None:
            f = 10.0 ** (-0.4 * (y - np.median(y)))   # mag -> relative flux
            used = mcol
        else:
            f = y / np.median(y)                      # normalize
            used = fcol

        pipe = ('SPOC' if h0.get('ORIGIN') == 'NASA/Ames'
                else 'TGLC' if h0.get('ORIGIN') == 'UCSB/TGLC'
                else 'QLP' if h0.get('ORIGIN') == 'MIT/QLP'
                else 'T16')

        return t, f, pipe, h0.get('SECTOR'), used, h0.get('TESSMAG')


def load_target(lc_root, tic, pipeline=None, sectors=None):
    """read light curves, combines according to given pipeline or sector (available for multiple sector analysis)"""
    files = fits_files_for(lc_root, tic)
    if not files:
        raise FileNotFoundError(f"TIC {tic}: {lc_root} no files/folders found")

    lcs = []
    for path in files:
        try:
            lcs.append(read_lc(path))
        except ValueError:
            continue

    if not lcs:
        raise ValueError(f"TIC {tic}: no readable fits file found")

    if pipeline:
        match = [l for l in lcs if l[2] == pipeline]
        if match:
            lcs = match

    if sectors:
        wanted = {s.strip() for s in str(sectors).split("-")}
        match = [l for l in lcs if str(l[3]) in wanted]
        if match:
            lcs = match

    t = np.concatenate([l[0] for l in lcs])
    f = np.concatenate([l[1] for l in lcs])
    order = np.argsort(t)
    return t[order], f[order]

def phase_fold(time, flux, period, t_0):
    """phase the light curve and show it in -0.25 and 0.75 so both primary and secondary will be shown."""
    ph = ((time - t_0) / period + 0.25) % 1 - 0.25
    order = np.argsort(ph)
    return ph[order], flux[order]

def flux_limits(flux, margin=0.05, clip=0.1):
    """y-axis limitor"""
    lo, hi = np.percentile(flux, [clip, 100.0 - clip])
    span = hi - lo if hi > lo else 1.0
    return lo - margin * span, hi + margin * span

if __name__ == "__main__":
    import time as timer

    from catalogue import load_catalogue

    df = load_catalogue("records.csv")
    row = df.iloc[0]

    t_start = timer.perf_counter()
    t, flux = load_target("fits", row["tic"], row["pipeline"], row["sectors"])
    t_read = timer.perf_counter()

    ph, pf = phase_fold(t, flux, row["period"], row["t_0"])
    t_phase = timer.perf_counter()

    print(f"TIC {row['tic']}  pipeline={row['pipeline']}  sectors={row['sectors']}")
    print(f"number of pts : {len(t)}")
    print(f"readout time : {(t_read - t_start) * 1000:7.1f} ms")
    print(f"phasing      : {(t_phase - t_read) * 1000:7.1f} ms")
    print(f"phase range: {ph.min():.3f} .. {ph.max():.3f}")