import pandas as pd

df = pd.read_csv("data/raw/companies.csv", encoding="utf-8-sig")
url_ok = df["url"].notna() & (df["url"].str.strip() != "")

print(f"전체: {len(df)}개")
print(f"URL 확보: {url_ok.sum()}개  ({url_ok.sum()/len(df)*100:.1f}%)")
print(f"URL 미발견: {(~url_ok).sum()}개")
print()

def src(s):
    return s.split("|")[0] if isinstance(s, str) else "unknown"

df["src"] = df["sources"].apply(src)
print("소스별 URL 확보율:")
for s, grp in df.groupby("src"):
    ok = (grp["url"].notna() & (grp["url"].str.strip() != "")).sum()
    print(f"  {s}: {ok}/{len(grp)} ({ok/len(grp)*100:.1f}%)")

print()
print("업종별 URL 확보 수:")
print(df[url_ok]["industry"].value_counts().to_string())
