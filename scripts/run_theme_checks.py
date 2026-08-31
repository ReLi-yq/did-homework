"""T1-T5 研究主题特定稳健性检验。

对应作业 Part A 2.4。针对"数字化转型 → 企业生产率"主题：
- T1 处理变量测量方式（连续处理强度）
- T2 异质性检验（行业 / 所有制 / 规模）
- T3 机制检验（digital × managerial_capability 互补性）
- T4 排除竞争性解释（industry × year 固定效应）
- T5 更严格：industry × year + province × year 固定效应

输出：output/robustness/robustness_table_t1_t5.csv
"""
from pathlib import Path
import warnings
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "raw" / "digital_transformation_firm_panel.csv"
OUT = ROOT / "output"
ROBUST = OUT / "robustness"
ROBUST.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(DATA_FILE)
BASE = "log_tfp ~ digital + capital_intensity + C(firm_id) + C(year)"


def fit(formula, data, cluster_col):
    model = smf.ols(formula, data=data)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return model.fit(cov_type="cluster", cov_kwds={"groups": data[cluster_col]})


def t1():
    """T1 处理变量的测量方式：连续数字化强度（处理组按其管理能力标准化，对照组为0）。"""
    d = df.copy()
    mc = d.groupby("firm_id")["managerial_capability"].transform("first")
    d["mc_std"] = (mc - mc.mean()) / mc.std()
    d["digital_intensity"] = d["digital"] * d["mc_std"]
    res = fit("log_tfp ~ digital_intensity + capital_intensity + C(firm_id) + C(year)", d, "firm_id")
    return {
        "T1_intensity_est": res.params["digital_intensity"],
        "T1_intensity_se": res.bse["digital_intensity"],
        "T1_intensity_p": res.pvalues["digital_intensity"],
    }


def t2():
    """T2 异质性检验：行业 / 所有制 / 规模分组。"""
    out = {}
    for ind in ["electronics", "textile"]:
        sub = df[df["industry"] == ind]
        res = fit(BASE, sub, "firm_id")
        out[f"T2_ind_{ind}_est"] = res.params["digital"]
        out[f"T2_ind_{ind}_se"] = res.bse["digital"]
    for soe in [1, 0]:
        sub = df[df["soe"] == soe]
        res = fit(BASE, sub, "firm_id")
        out[f"T2_soe_{soe}_est"] = res.params["digital"]
    size_mean = df.groupby("firm_id")["firm_size"].mean()
    med = size_mean.median()
    for grp, cond in [("large", size_mean >= med), ("small", size_mean < med)]:
        sub = df[df["firm_id"].isin(size_mean[cond].index)]
        res = fit(BASE, sub, "firm_id")
        out[f"T2_size_{grp}_est"] = res.params["digital"]
    return out


def t3():
    """T3 机制检验：digital × managerial_capability 互补性。"""
    d = df.copy()
    d["mc"] = d.groupby("firm_id")["managerial_capability"].transform("first")
    d["digital_x_mc"] = d["digital"] * d["mc"]
    res = fit("log_tfp ~ digital + digital_x_mc + capital_intensity + C(firm_id) + C(year)", d, "firm_id")
    return {
        "T3_digital_est": res.params["digital"],
        "T3_interact_est": res.params["digital_x_mc"],
        "T3_interact_se": res.bse["digital_x_mc"],
        "T3_interact_p": res.pvalues["digital_x_mc"],
    }


def t4():
    """T4 排除竞争性解释：industry × year 固定效应。"""
    d = df.copy()
    d["ind_year"] = d["industry"].astype(str) + "_" + d["year"].astype(str)
    res = fit("log_tfp ~ digital + capital_intensity + C(firm_id) + C(ind_year)", d, "firm_id")
    return {
        "T4_ind_year_est": res.params["digital"],
        "T4_ind_year_se": res.bse["digital"],
        "T4_ind_year_p": res.pvalues["digital"],
    }


def t5():
    """T5 更严格：industry × year + province × year 固定效应。"""
    d = df.copy()
    d["ind_year"] = d["industry"].astype(str) + "_" + d["year"].astype(str)
    d["prov_year"] = d["province"].astype(str) + "_" + d["year"].astype(str)
    res = fit("log_tfp ~ digital + capital_intensity + C(firm_id) + C(ind_year) + C(prov_year)", d, "firm_id")
    return {
        "T5_indprov_year_est": res.params["digital"],
        "T5_indprov_year_se": res.bse["digital"],
        "T5_indprov_year_p": res.pvalues["digital"],
    }


def main():
    summary = {}
    checks = {"T1": t1, "T2": t2, "T3": t3, "T4": t4, "T5": t5}
    for name, fn in checks.items():
        try:
            summary.update(fn())
            print(f"[OK] {name}")
        except Exception as e:
            summary[name] = f"ERROR: {e}"
            print(f"[ERR] {name}: {e}")
    pd.DataFrame([summary]).T.to_csv(ROBUST / "robustness_table_t1_t5.csv", header=False)
    print(f"\nWrote {ROBUST / 'robustness_table_t1_t5.csv'}")
    for k, v in summary.items():
        print(f"{k} = {v}")


if __name__ == "__main__":
    main()
