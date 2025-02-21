import streamlit as st
import pandas as pd

from data import team
import pk_shootout

if 'pk' not in st.session_state:
    st.session_state.pk = pk_shootout.PKShootout()

kt = team.KickingTeam

st.markdown("# :soccer: Welcome to the World Cup PK simluator! :soccer:")
st.markdown(
    "### Have you ever been watching a PK shootout and wondered 'What are each teams chances of "
    "winning?' Well no need to wonder any longer."
)
st.write("Further details below")

st.markdown("#### Play Here")

# Button to track clicks
col1, col2 = st.columns(2)
with col1:
    if st.button('KICK - :white_check_mark:'):
        st.session_state.pk.kick(kick_success=True)

with col2:
    if st.button('KICK - ❌'):
        st.session_state.pk.kick(kick_success=False)

# Button to reset the count
if st.button('Reset Count', type='tertiary'):
    st.session_state.pk.reset_shootout()


st.markdown(f"### Team Kicking: {st.session_state.pk.kicking_team.value}")

# Display the number of clicks
if st.session_state.pk.n_kicks_attempted < 10:
    st.write(f'Kick number {st.session_state.pk.n_kicks_attempted + 1}')
else:
    st.write(f'Kick number {st.session_state.pk.n_kicks_attempted}')

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
    st.markdown("#### TEAM 1")
    st.write(f"Shot attempts: {team_1_dict['kicks_attempted']}")
    st.write(f"Goals: {team_1_dict['score']}")
    st.write(f"Win probability: {team_1_dict['probability']:.2%}")
with col2:
    team_2_dict = st.session_state.pk.shootout_team_progress[kt.team_2.value]
    st.markdown("#### TEAM 2")
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

st.markdown(""" 
#### Instructions

To play this simulator, you only need to click 2 buttons -- one for a miss and one for a make.
After each kick, the simluator always switches to the next team kicking. You can track the score of
 the shootout and each team's probabilities throughout. 

A few simple rules/explanations:
- This simulator is only built to handle 10 kicks. If the shootout is tied after 10 kicks, we end
the shootout and give each team a 50/50 shot to win.
- Probabilities are determined empiricially based on the history of the world cup. For example, if
the shootout is 2-2 after 4 kicks, I look at every shootout in World Cup history that was 2-2 after
4 kicks and determine each teams odds of winning based on this history.
- There have only been 36 shootouts ever in World Cup play, so we have plently of scores that have
never happened. If this is the case, I essentially simulate kicks until we either reach the end of
the shootout or until we reach another emprical probability in order to calculate the probability
each team has of winning.
- This is quite new and hacky, so please let me know if you have any feedback!
""")
