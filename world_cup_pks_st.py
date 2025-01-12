import streamlit as st
import pandas as pd

from data import team
import pk_shootout

if 'pk' not in st.session_state:
    st.session_state.pk = pk_shootout.PKShootout()

kt = team.KickingTeam

st.title("Penalty Shootout Simulator")

# Button to track clicks
col1, col2 = st.columns(2)
with col1:
    if st.button('KICK - Make'):
        st.session_state.pk.kick(kick_success=True)

with col2:
    if st.button('KICK - Miss'):
        st.session_state.pk.kick(kick_success=False)

# Button to reset the count
if st.button('Reset Count'):
    st.session_state.pk.reset_shootout()

st.header(f"Team Kicking: {st.session_state.pk.kicking_team.value}")

# Display the number of clicks
st.write(f'Kick number {st.session_state.pk.n_kicks_attempted + 1}')

team_1_score = str(
    st.session_state.pk.shootout_team_progress[kt.team_1.value]['score']
)
team_2_score = str(
    st.session_state.pk.shootout_team_progress[kt.team_2.value]['score']
)
# display the score
st.header(f"Score: {team_1_score} - {team_2_score}")

if st.session_state.pk.shootout_is_over:
    st.write(f"SHOOTOUT IS OVER!")

# put the team 1 and team 2 stats in their own columns
col1, col2 = st.columns(2)
with col1:
    team_1_dict = st.session_state.pk.shootout_team_progress[kt.team_1.value]
    st.subheader("TEAM 1")
    st.write(f"Shot attempts: {team_1_dict['kicks_attempted']}")
    st.write(f"Goals: {team_1_dict['score']}")
    st.write(f"Win probability: {team_1_dict['probability']:.2%}")
with col2:
    team_2_dict = st.session_state.pk.shootout_team_progress[kt.team_2.value]
    st.subheader("TEAM 2")
    st.write(f"Shot attempts: {team_2_dict['kicks_attempted']}")
    st.write(f"Goals: {team_2_dict['score']}")
    st.write(f"Win probability: {team_2_dict['probability']:.2%}")

shootout_progress_df = pd.DataFrame.from_dict(
    st.session_state.pk.shootout_progress, orient='index'
).T
# switch this to altair_chart
st.line_chart(
    data=shootout_progress_df,
    x="kick",
    y=["team_1_probability", "team_2_probability"],
)

# st.table(
#     data=pd.DataFrame.from_dict(
#         st.session_state.pk.shootout_progress, orient='index'
#     ).reset_index().rename(columns={'index': 'kick', 0: 'kick_result'})
# )

# STILL NEED TO FIGURE OUT RESETS IN A CLEANER WAY
# NEED TO HANDLE PROBABILITY GAPS
# ADD A PLOT - X IS KICK NUMBER AND Y IS THE AXIS
# NEED TO BETTER "END" THE SHOOTOUTS