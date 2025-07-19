from otree.api import *
import random
import time


doc = """
Stage 2 (BDM) of save-invest experiment
Participants state a certain equivalent (CE) at which they are indifferent between a given lottery and a sure payout.
"""


class C(BaseConstants):
    NAME_IN_URL = 'stage2'
    PLAYERS_PER_GROUP = None
    
    # total rounds is 32 (42 - 10)
    NUM_ROUNDS = 32

    # round order will not be randomized


class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    pass


class Player(BasePlayer):
    inflection_input = models.FloatField(
        doc="Participant's stated CE for the lottery"
    )
    start_time = models.FloatField()
    reaction_time = models.FloatField()
    random_price = models.CurrencyField()

# Error Messages for incorrect user inputs
def inflection_input_error_message(self, value):
    # CE must lie between lottery outcomes
    pr = self.round_number - 1
    low = min(self.participant.s2monthA[pr], self.participant.s2monthB[pr])
    high = max(self.participant.s2monthA[pr], self.participant.s2monthB[pr])
    if value < low or value > high:
        return f"Please enter a value between {low} and {high}."


# PAGES

class InstructionsStageTwo(Page):
    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == 1

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        if player.round_number == 1:
            participant = player.participant
            participant.rts_bdm = []
            
            # randomly select paying round
            # participant.paying_round_stage_2 = random.randint(1, C.NUM_ROUNDS)
            # participant.length created for the demo (shortening the length of the experiment)
            participant.paying_round_stage_2 = random.randint(1, participant.length)
            # position in the list
            pr = participant.paying_round_stage_2 - 1
            
            # draw a random price between lottery outcomes
            low = min(participant.s2monthA[pr], participant.s2monthB[pr])
            high = max(participant.s2monthA[pr], participant.s2monthB[pr])
            participant.random_price = round(random.uniform(low, high), 2)

            # randomly select a paying round across 42+32 situations; since the previous code has already drawn a random round from both stage 1 and stage 2, now we are deciding which round to apply (if we were to choose one out of 42+32)
            participant.final_paying_round= random.randint(1, participant.length + len(participant.probA))
            


class BdmPage(Page):
    form_model = 'player'
    form_fields = ['inflection_input']

    @staticmethod
    def is_displayed(player: Player):
        return True

    @staticmethod
    def vars_for_template(player: Player):
        # record start time
        player.start_time = time.time()
        # collect data for each BDM Page
        pr_ = player.round_number - 1
        participant = player.participant
        payment_today = participant.s2savings[pr_]
        monthA = participant.s2monthA[pr_]
        monthB = participant.s2monthB[pr_]
        probA = int(round(participant.s2probA[pr_] * 100))
        probB = int(round(participant.s2probB[pr_] * 100))
        low = min(monthA, monthB)
        high = max(monthA, monthB)
        return dict(
            payment_today=payment_today,
            monthA=monthA,
            monthB=monthB,
            probA=probA,
            probB=probB,
            low=low,
            high=high,
        )

    # store reactions times
    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        player.reaction_time = time.time() - player.start_time
        player.participant.rts_bdm.append(player.reaction_time)


class Results(Page):
    @staticmethod
    def is_displayed(player: Player):
        # return player.round_number == C.NUM_ROUNDS
        return player.round_number == player.participant.length

    @staticmethod
    def vars_for_template(player: Player):
        participant = player.participant
        pr = participant.paying_round_stage_2 - 1
        paying_player = player.in_round(participant.paying_round_stage_2)
        ce = paying_player.inflection_input
        rp = participant.random_price
        fpr = participant.final_paying_round
        # stage2 today payoff
        participant.payoff_today_s2 = participant.s2savings[pr]
        # stage2 one-month payoff via BDM
        if rp < ce:
            # if there is only asset A
            if participant.s2probB[pr] == 0:
                participant.payoff_one_month_s2 = participant.s2monthA[pr]
                executed_asset = 'A'
            else:
                participant.payoff_one_month_s2 = random.choices(
                    [participant.s2monthA[pr], participant.s2monthB[pr]],
                    weights=[participant.s2probA[pr], participant.s2probB[pr]],
                    k=1
                )[0]
                executed_asset = 'A' if participant.payoff_one_month_s2 == participant.s2monthA[pr] else 'B'
            method = 'Lottery'
        else:
            participant.payoff_one_month_s2 = rp
            executed_asset = None
            method = 'Sure amount'

        # stage2 executed assets combination
        exec_probA  = participant.s2probA[pr] * 100
        exec_probB  = participant.s2probB[pr] * 100
        exec_monthA = participant.s2monthA[pr]
        exec_monthB = participant.s2monthB[pr]
        
        # total payoff (stage 1 + stage 2) including fixed payment 
        total_today = participant.payoff_today_s1 + participant.payoff_today_s2 + 5
        total_1m =  participant.payoff_one_month_s1 + participant.payoff_one_month_s2 + 5

        # final payoff (one out of 42+32), including fixed payment
        if fpr < len(participant.probA) + 1: # sectu
            final_today = participant.payoff_today_s1 + 5
            final_1m =  participant.payoff_one_month_s1 + 5
            pay_stage = 1
            pay_round = participant.paying_round
        else:
            final_today = participant.payoff_today_s2 + 5
            final_1m =  participant.payoff_one_month_s2 + 5
            pay_stage = 2
            pay_round = participant.paying_round_stage_2
        
        return dict(
            # gets stage 1 results
            payoff_today_s1 = participant.payoff_today_s1,
            paying_asset_s1 = participant.paying_asset,
            payoff_one_month_s1 = participant.payoff_one_month_s1,
            payinground_s1 = participant.paying_round,
            # gets stage 2 results
            payinground_s2 = participant.paying_round_stage_2,
            exec_probA = exec_probA,
            exec_probB = exec_probB,
            exec_monthA = exec_monthA,
            exec_monthB = exec_monthB,
            executed_asset = executed_asset,
            payoff_today_s2 = participant.payoff_today_s2,
            payoff_one_month_s2 = participant.payoff_one_month_s2,
            # BMD results
            random_price = rp,
            ce = ce,
            method = method,
            # total payoff including fixed payment (one from 42 + one from 32)
            total_today = total_today,
            total_1m = total_1m,
            # final payoff including fixed payment (one from 42 + 32)
            final_today = final_today, 
            final_1m = final_1m,
            pay_stage = pay_stage,
            pay_round = pay_round,
        )


page_sequence = [
    InstructionsStageTwo,
    BdmPage,
    Results
]
