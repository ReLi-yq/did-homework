"""复现 DID 主回归（干净版）。

修复课堂脚本 analyze_did.py 的问题：
- 移除被企业固定效应吸收的 time-invariant 变量（soe、export_share），
  消除设计矩阵秩亏，使聚类标准误不再为 NaN。
- 保留处理变量 digital 与随时间变化的协变量 capital_intensity。
"""
from pathlib import Path
import warnings

import pandas as pd
import statsmodels.formula.api as smf

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "raw" / "digital_transformation_firm_panel.csv"
OUT_FILE = ROOT / "output" / "main_did_results.csv"


def main() -> None:
    df = pd.read_csv(DATA_FILE)
    # 主回归：digital + capital_intensity + 企业FE + 年份FE，聚类到企业
    model = smf.ols(
        "log_tfp ~ digital + capital_intensity + C(firm_id) + C(year)",
        data=df,
    )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        result = model.fit(cov_type="cluster", cov_kwds={"groups": df["firm_id"]})

    row = {
        "term": "digital",
        "estimate": result.params["digital"],
        "std_error_cluster_firm": result.bse["digital"],
        "t_value": result.tvalues["digital"],
        "p_value": result.pvalues["digital"],
        "n_obs": int(result.nobs),
    }
    out = pd.DataFrame([row])
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT_FILE, index=False)

    print(f"DID coefficient (digital)      = {row['estimate']:.6f}")
    print(f"Clustered std. error (firm)    = {row['std_error_cluster_firm']:.6f}")
    print(f"t-value                        = {row['t_value']:.3f}")
    print(f"p-value                        = {row['p_value']:.4f}")
    print(f"N obs                          = {row['n_obs']}")
    print(f"Wrote {OUT_FILE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
