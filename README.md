An interactive tool for validation and vetting of TESS light curves of eclipsing binaries. 

You can run the interactive tool easily by 

```bash
python validate_eclipses.py
```

This will activate the GUI and displays the light curve of your available targets, as it is shown below. 


<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="/gui_example.png">
    <img alt="search_eclipses" src="assets/logo-light.svg" width="440">
  </picture>
</p>


Please note that this program uses **\*.fits** files to generate time series and phased light curves. Also, in order to phase the light curve, a prior information of t0 and P is required. 

In my test case, I generated all the periods and t0s from [ECLIPSR](https://github.com/LucIJspeert/eclipsr) code. After, I saved my results with to `results.csv` (this is what the program reads as the prior eclipse information). 

The code also utilizes key shortcuts which enables to assign different decisions/verdicts according to your final decision. 

I briefly describe what keyboard shortcuts do below.

| Keyboard Shortcut | Action |
| --- | --- |
| `F1` | accepts the object with the parameter configuration shown in screen | 
| `F2` | rejects the object from the sample|
| `F3` | flags for uncertain, if no final decision is made|
| `F4` | period will be fixed to what is shown in screen. If you phased it to 2P or P/2, period will be fixed to that.|
| `F5` | phase will be fixed according to the changes you make, similar effects with period|
| `F6` | flag the target if there is no eclipse seen or detected |
| `F7` | flag the target if the quality of data is relatively low|
| `← →` |  allows to move between objects without making any changes |
| `↑ ↓` |  change the period of phased light curves by multiple ratios of P. Available settings: P/4, P/3, P/2, P, 2P, 3P, 4P|
| `[` & `]` | allows to shift the phase by 0.005 steps of phase units|
| `{` & `}` | allows to shift the phase by 0.05 steps of phase units|

To reset the changes, press `0` or to save your decisions of adjustments, press `Enter`.

## Citation

If you use this code, please cite: 
- Kutluay et al., in prep --- An eclipsing binary catalogue in PLATO LOPS2 field.


