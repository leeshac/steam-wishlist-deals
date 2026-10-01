import streamlit as st
from pipeline import main

#function that highlights a row based on a condition
def highlight_steam(row):

    if row.name == 0 and row["store_name"] == "Steam":
        return ["background-color: #21235c" if i % 2 == 0 else "background-color: #385922" for i in range(len(row))]
    
    elif row["store_name"] == "Steam":
        return ["background-color: #21235c"] * len(row)

    elif row.name == 0:
        return ["background-color: #385922"] * len(row)

    return [""] * len(row)

st.title("Steam Wishlist Deals")

user_id = st.text_input("Enter your Steam ID")

st.markdown("<div style='margin-bottom: 25px;'></div>", unsafe_allow_html=True)

#legend for the colors used in the table
st.markdown("""
<div style=" padding: 10px; display: flex; align-items: center; justify-content: center; width: 100%;">
<div style="display: flex; gap: 30px;">
<span style="background-color:#21235c; color:white; padding:4px 10px;border-radius: 6px;"> Steam deal </span>
<span style="background-color:#385922; color:white; padding:4px 10px;border-radius: 6px;"> Best deal </span>
</div>
</div>
""", unsafe_allow_html=True)

st.markdown("<div style='margin-bottom: 25px;'></div>", unsafe_allow_html=True)

st.markdown("""
<style>
    div.stButton > button {width: 180px; height: 50px; border-radius: 6px; font-size: 20px;}
</style>
""", unsafe_allow_html=True)

if st.button("Find Deals"):
    results = main(user_id)

    for game_name, game_data in results.groupby("game_name"):
        st.subheader(game_name)
        game_data = game_data.reset_index(drop=True)
        styled_data = game_data.style.apply(highlight_steam, axis=1)
        st.dataframe(styled_data, use_container_width=True)
