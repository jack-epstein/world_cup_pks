# World Cup PK Shootout

Welcome to the World Cup PK simluator!

Have you ever been watching a PK shootout and wondered "What are each teams chances of winning?" Well no need to wonder any longer. 

To play this simulator, you only need to click 2 buttons -- one for a miss and one for a make. After each kick, the simluator always switches to the next team kicking. You can track the score of the shootout and each team's probabilities throughout. 

A few simple rules/explanations:
- This simulator is only built to handle 10 kicks. If the shootout is tied after 10 kicks, we end the shootout and give each team a 50/50 shot to win.
- Probabilities are determined empiricially based on the history of the world cup. For example, if the shootout is 2-2 after 4 kicks, I look at every shootout in World Cup history that was 2-2 after 4 kicks and determine each teams odds of winning based on this history.
- There have only been 36 shootouts ever in World Cup play, so we have plently of scores that have never happened. If this is the case, I essentially simulate kicks until we either reach the end of the shootout or until we reach another emprical probability in order to calculate the probability each team has of winning.
- This is quite new and hacky, so please let me know if you have any feedback!

[Play here](https://worldcup-pk-simulator.streamlit.app/)
