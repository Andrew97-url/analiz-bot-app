import streamlit as st
import pandas as pd
import sqlite3
import os

DB_NAME = "futbol_verileri.db"

def get_db_data():
    if not os.path.exists(DB_NAME): return None
    try:
        conn = sqlite3.connect(DB_NAME)
        df = pd.read_sql_query("SELECT * FROM maclar", conn)
        conn.close()
        df.columns = [c.lower().strip() for c in df.columns]
        for col in ['b365h', 'b365d', 'b365a']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').round(2)
        return df.dropna(subset=['b365h', 'b365d', 'b365a'])
    except: return None

def bulten_yukle():
    if not os.path.exists('fixtures.csv'): return None, None, None
    try:
        df = pd.read_csv('fixtures.csv')
        df.columns = df.columns.str.strip()
        t_col = next((c for c in ['Date','date','Tarih','Time'] if c in df.columns), None)
        for col in ['B365H', 'B365D', 'B365A']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').round(2)
        pos = ['League','Div','LIG','league','lig']
        l_col = next((c for c in pos if c in df.columns), df.columns[0])
        return df.dropna(subset=['B365H','B365D','B365A']), l_col, t_col
    except: return None, None, None

def ai_karar(iy05, ms15, ms25, kgv, kor, iy15, tot):
    t = []
    if tot < 5: return t
    if ms15 >= 85: t.append(f"🛡️ MS 1.5 ÜST (%{ms15:.0f})")
    if iy05 >= 75: t.append(f"✅ İY 0.5 ÜST (%{iy05:.0f})")
    if iy15 >= 50: t.append(f"⚡ İY 1.5 ÜST (%{iy15:.0f}) - RİSKLİ")
    if ms25 >= 75: t.append(f"🔥 MS 2.5 ÜST (%{ms25:.0f})")
    if kgv >= 75: t.append(f"🤝 KG VAR (%{kgv:.0f})")
    if kor >= 75: t.append(f"🚩 KORNER 8.5 ÜST (%{kor:.0f})")
    return t

st.set_page_config(page_title="AI Analiz Pro", layout="wide")
st.title("🤖 Gelişmiş AI Analiz Paneli")

bulten, lig_col, b_tarih = bulten_yukle()

if bulten is not None:
    ligler = sorted(bulten[lig_col].unique().astype(str).tolist())
    s_lig = st.sidebar.selectbox("📂 Lig Seçiniz", ligler)
    l_maclar = bulten[bulten[lig_col].astype(str) == s_lig].copy()
    h_c = next((c for c in ['HomeTeam','Home','Ev'] if c in bulten.columns), bulten.columns[0])
    a_c = next((c for c in ['AwayTeam','Away','Deplasman'] if c in bulten.columns), bulten.columns[1])
    
    st.subheader(f"🏟️ {s_lig} Bülteni")
    st.dataframe(l_maclar[[b_tarih, h_c, a_c, 'B365H', 'B365D', 'B365A']], use_container_width=True)

    st.markdown("---")
    opts = l_maclar.apply(lambda r: f"{r[b_tarih]} | {r[h_c]} - {r[a_c]}", axis=1).tolist()
    choice = st.selectbox("🎯 Karşılaşma Seçin", opts)

    if st.button("🔍 Analizi Başlat"):
        idx = opts.index(choice)
        row = l_maclar.iloc[idx]
        ho, do, ao = row['B365H'], row['B365D'], row['B365A']
        db = get_db_data()
        if db is not None:
            f1, f2, f3 = (db['b365h']==ho), (db['b365d']==do), (db['b365a']==ao)
            m = db[f1 & f2 & f3].copy()
            if not m.empty:
                tot = len(m)
                fthg = next((c for c in ['fthg','hg'] if c in m.columns), 'fthg')
                ftag = next((c for c in ['ftag','ag'] if c in m.columns), 'ftag')
                hthg = next((c for c in ['hthg','iy_hg'] if c in m.columns), 'hthg')
                htag = next((c for c in ['htag', 'iy_ag'] if c in m.columns), 'htag')
                hc, ac = 'hc', 'ac'

                v_hg, v_ag = m[fthg].fillna(0).astype(float), m[ftag].fillna(0).astype(float)
                v_iyh, v_iya = m[hthg].fillna(0).astype(float), m[htag].fillna(0).astype(float)
                v_hc = m[hc].fillna(0).astype(float) if hc in m.columns else pd.Series([0]*tot)
                v_ac = m[ac].fillna(0).astype(float) if ac in m.columns else pd.Series([0]*tot)

                ms_g, iy_g, ko_t = (v_hg+v_ag), (v_iyh+v_iya), (v_hc+v_ac)
                
                p_ms1, p_ms0, p_ms2 = (len(m[v_hg > v_ag])/tot)*100, (len(m[v_hg == v_ag])/tot)*100, (len(m[v_ag > v_hg])/tot)*100
                p_iy15 = (len(m[iy_g > 1.5])/tot)*100
                p15, p25 = (len(m[ms_g>1.5])/tot)*100, (len(m[ms_g>2.5])/tot)*100
                p_iy, p_kg = (len(m[iy_g>0])/tot)*100, (len(m[(v_hg>0)&(v_ag>0)])/tot)*100
                p_ko85 = (len(m[ko_t>8.5])/tot)*100 if ko_t.sum()>0 else 0

                st.markdown("### 🧠 AI Karar Merkezi")
                tav = ai_karar(p_iy, p15, p25, p_kg, p_ko85, p_iy15, tot)
                
                # HATA VEREN KISIM STANDART HALE GETİRİLDİ:
                if tav:
                    for t in tav:
                        st.success(t)
                else:
                    st.info("Sinyal yok.")

                st.markdown("#### 🏆 Maç Sonucu (1-0-2) Dağılımı")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Ev Sahibi (1)", f"%{p_ms1:.0f}")
                c2.metric("Beraberlik (0)", f"%{p_ms0:.0f}")
                c3.metric("Deplasman (2)", f"%{p_ms2:.0f}")
                c4.metric("Geçmiş Maç", tot)

                st.markdown("#### ⚽ Gol ve Korner Analizi")
                g1, g2, g3, g4, g5, g6 = st.columns(6)
                g1.metric("MS 1.5 Üst", f"%{p15:.0f}")
                g2.metric("MS 2.5 Üst", f"%{p25:.0f}")
                g3.metric("İY 0.5 Üst", f"%{p_iy:.0f}")
                g4.metric("İY 1.5 Üst", f"%{p_iy15:.0f}")
                g5.metric("KG Var", f"%{p_kg:.0f}")
                g6.metric("Korner 8.5+", f"%{p_ko85:.0f}")
                
                st.markdown("---")
                m['ms_s'] = v_hg.astype(int).astype(str) + " - " + v_ag.astype(int).astype(str)
                m['iy_s'] = v_iyh.astype(int).astype(str) + " - " + v_iya.astype(int).astype(str)
                m['ko_s'] = v_hc.astype(int).astype(str) + " - " + v_ac.astype(int).astype(str)
                
                d_date = next((c for c in ['date','tarih'] if c in m.columns), 'date')
                d_home = next((c for c in ['hometeam','home'] if c in m.columns), 'home')
                d_away = next((c for c in ['awayteam', 'away'] if c in m.columns), 'away')
                res = m[[d_date, d_home, d_away, 'ms_s', 'iy_s', 'ko_s']].copy()
                res.columns = ['Tarih', 'Ev Sahibi', 'Deplasman', 'MS', 'İY', 'Korner']
                st.dataframe(res, use_container_width=True)
            else: st.warning("Maç bulunamadı.")
else: st.error("fixtures.csv yok.")