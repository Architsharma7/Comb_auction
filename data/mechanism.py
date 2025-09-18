from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass(frozen=True)
class Trade:
    id: str
    sell_token: str
    buy_token: str
    score: int


@dataclass(frozen=True)
class Solution:
    id: str
    solver: str
    score: int
    trades: list[Trade]
    
def get_orders(solutions: list[Solution]):
    return {trade.id for solution in solutions for trade in solution.trades}


def aggregate_scores(solution: Solution) -> dict[tuple[str, str], int]:
    """Aggregates scores for trades by token pairs in a solution.

    This function processes a given solution containing trades and aggregates the
    scores for each unique token pair (sell_token, buy_token). The result is a
    dictionary where the keys are tuples representing token pairs, and the values
    are the aggregated score for that pair. The function iterates through the
    trades in the solution, summing the scores for trades with the same token pair.

    Parameters
    ----------
    solution : Solution
        An instance of the Solution class, which contains a list of trade objects.

    Returns
    -------
    dict[tuple[str, str], int]
        A dictionary where the keys are tuples of type (str, str), representing the
        token pairs (sell_token, buy_token), and the values are integers
        representing the aggregated score for each pair.

    """
    scores: dict[tuple[str, str], int] = {}
    for trade in solution.trades:
        scores[(trade.sell_token, trade.buy_token)] = (
            scores.get((trade.sell_token, trade.buy_token), 0) + trade.score
        )
    return scores


def compute_baseline_solutions(
    solutions: list[Solution],
) -> dict[tuple[str, str], Solution]:
    """Compute baseline solutions from a list of solutions.

    This function processes a list of `Solution` objects to determine the baseline
    solutions by analyzing their aggregated scores. For each token pair present in
    the aggregated scores, the function compares scores and selects the solution
    with the highest score for each unique token pair.

    Parameters
    ----------
    solutions: list of Solution
        A list of `Solution` objects to be analyzed. Each solution contains
        information, including an associated aggregated scores mapping
        token pairs to scores.

    Returns
    -------
    baseline_solutions: dict[tuple[str, str], Solution]
        A dictionary where keys are token pairs (tuples of two strings)
        and values are the baseline `Solution` objects associated with
        the highest score for each token pair.
    """
    baseline_solutions: dict[tuple[str, str], Solution] = {}
    for solution in solutions:
        aggregated_scores = aggregate_scores(solution)
        if len(aggregated_scores) > 1:
            continue
        for token_pair, score in aggregated_scores.items():
            if (
                token_pair not in baseline_solutions
                or score > baseline_solutions[token_pair].score
            ):
                baseline_solutions[token_pair] = solution

    return baseline_solutions


class SolutionFilter(ABC):
    @abstractmethod
    def filter(self, solutions: list[Solution]) -> list[Solution]:
        """Filter solutions"""
        
@dataclass(frozen=True)
class BaselineFilter(SolutionFilter):
    def filter(self, solutions: list[Solution]) -> list[Solution]:
        filtered_solutions = []
        baseline_solutions = compute_baseline_solutions(solutions)
        for solution in solutions:
            aggregated_scores = aggregate_scores(solution)
            if len(aggregated_scores) == 1 or all(
                score
                >= (
                    sum(
                        (
                            trade.score
                            for trade in baseline_solutions[token_pair].trades
                        ),
                        0,
                    )
                    if token_pair in baseline_solutions
                    else 0
                )
                for token_pair, score in aggregated_scores.items()
            ):
                filtered_solutions.append(solution)
        return filtered_solutions

        
class BatchCompatibilityFilter(ABC):
    @abstractmethod
    def get_filter_set(self, solution: Solution) -> set:
        pass


class DirectedTokenPairs(BatchCompatibilityFilter):
    def get_filter_set(self, solution: Solution) -> set:
        return {(trade.sell_token, trade.buy_token) for trade in solution.trades}
    
class SolutionSelection(ABC):
    @abstractmethod
    def select_solutions(self, solutions: list[Solution]) -> list[Solution]:
        """Select solutions from a list of solutions.

        Solutions selected should be executable at the same time.
        """
        
@dataclass(frozen=True)
class SubsetFilteringSelection(SolutionSelection):
    cumulative_filtering: bool = False
    batch_compatibility: BatchCompatibilityFilter = DirectedTokenPairs()

    def select_solutions(self, solutions: list[Solution]) -> list[Solution]:
        sorted_solutions = sorted(
            solutions, key=lambda _solution: _solution.score, reverse=True
        )
        selection: list[Solution] = []
        filter_set: set[str] = set()
        for solution in sorted_solutions:
            solution_filter_set = self.batch_compatibility.get_filter_set(solution)
            if len(solution_filter_set & filter_set) == 0:
                selection.append(solution)
                if (
                    not self.cumulative_filtering
                ):  # if not cumulative, only filter for selection
                    filter_set = filter_set.union(solution_filter_set)
            if self.cumulative_filtering:  # if cumulative, always filter
                filter_set = filter_set.union(solution_filter_set)

        return selection
    
class WinnerSelection(ABC):
    @abstractmethod
    def select_winners(self, solutions: list[Solution]) -> list[Solution]:
        """Select winners"""


@dataclass(frozen=True)
class DirectSelection(WinnerSelection):
    selection_rule: SolutionSelection

    def select_winners(self, solutions: list[Solution]) -> list[Solution]:
        return self.selection_rule.select_solutions(solutions)
    
class RewardMechanism(ABC):
    @abstractmethod
    def compute_rewards(
        self, winners: list[Solution], solutions: list[Solution]
    ) -> dict[str, int]:
        """
        Abstract method to compute rewards for solvers based on winners and solutions.

        This method calculates the rewards for solvers, mapping each solver to its
        respective reward value.

        It is expected to be overridden by concrete subclasses implementing specific reward
        computation strategies.

        Parameters
        ----------
        winners : list[Solution]
            A list of solutions that are marked as winners.
        solutions : list[Solution]
            A list of all solutions from which winners were selected.

        Returns
        -------
        dict[str, int]
            A dictionary where the keys are solvers and the values are the
            respective rewards (as integers in atoms of the native token).
        """
        
class NoReward(RewardMechanism):
    def compute_rewards(
        self, winners: list[Solution], solutions: list[Solution]
    ) -> dict[str, int]:
        return {winner.id: 0 for winner in winners}
    
class AuctionMechanism(ABC):
    @abstractmethod
    def winners_and_rewards(
        self, solutions: list[Solution]
    ) -> tuple[list[Solution], dict[str, int]]:
        """
        Determines the winners among the provided solutions and calculates their
        corresponding rewards.

        This method evaluates a list of solutions, identifies which ones are the
        winners based on a defined criterion, and assigns rewards accordingly.
        The winners are returned as a list, and the rewards are returned as a
        dictionary where the keys are identifiers of winning solvers, and the values
        represent the respective rewards.

        Parameters
        ----------
        solutions : list[Solution]
            A list of solution objects. Each solution contains information
            that is evaluated to determine if it qualifies as a winner.

        Returns
        -------
        tuple[list[Solution], dict[str, int]]
            A tuple containing:
            - A list of winning `Solution` objects.
            - A dictionary mapping solvers to their respective rewards.
        """


@dataclass(frozen=True)
class FilterRankRewardMechanism(AuctionMechanism):
    """
    FilterRankRewardMechanism class handles the combined operations of solution filtering, winner
    selection, and reward computation within an auction mechanism. It integrates these stages to
    determine winners and associated rewards.

    Attributes
    ----------
    solution_filter : SolutionFilter
        An instance responsible for filtering solutions based on predefined criteria.
    winner_selection : WinnerSelection
        An instance responsible for selecting winners from the filtered solutions.
    reward_mechanism : RewardMechanism
        An instance responsible for computing rewards for the selected winners.
    """

    solution_filter: SolutionFilter
    winner_selection: WinnerSelection
    reward_mechanism: RewardMechanism

    def winners_and_rewards(
        self, solutions: list[Solution]
    ) -> tuple[list[Solution], dict[str, int]]:
        filtered_solutions = self.solution_filter.filter(solutions)
        winners = self.winner_selection.select_winners(filtered_solutions)
        rewards = self.reward_mechanism.compute_rewards(winners, filtered_solutions)
        return winners, rewards
  
def remove_order_from_solution(solution: Solution, order_uids: set[str]):
    """Removes specific orders from a given solution based on a set of order unique IDs.

    This function is designed to filter out trades from a given solution object whose
    unique IDs are specified in the provided set of order IDs. The resulting solution
    will retain all attributes from the original except for the filtered trades, and
    the score will be recalculated based on the remaining trades.

    Parameters
    ----------
    solution : Solution
        The original solution object containing all trades and associated metadata.
    order_uids : set[str]
        A set of unique IDs representing the orders to be removed from the solution.

    Returns
    -------
    Solution
        A new solution object that contains only the trades not filtered out
        based on the provided order unique IDs, with an updated score.
    """
    trades_filtered = [trade for trade in solution.trades if trade.id not in order_uids]
    solution_filtered = Solution(
        id=solution.id,
        solver=solution.solver,
        score=sum(trade.score for trade in trades_filtered),
        trades=trades_filtered,
    )
    return solution_filtered  

def run_counter_factual_winners(
    auction_solutions_list: list[list[Solution]],
    mechanism: AuctionMechanism,
    remove_executed_orders: bool = True,
) -> list[list[Solution]]:
    """
    Same filtering of already-executed orders as run_counter_factual_analysis,
    but returns ONLY the list of winners per auction (no rewards).
    """
    winners_per_auction: list[list[Solution]] = []
    order_uids_settled: set[str] = set()

    for solutions in auction_solutions_list:
        # filter orders which are already settled
        if remove_executed_orders:
            solutions_filtered = [
                remove_order_from_solution(solution, order_uids_settled)
                for solution in solutions
            ]
            solutions_filtered = [
                s for s in solutions_filtered if s.score > 0
            ]
        else:
            solutions_filtered = list(solutions)

        winners, _ = mechanism.winners_and_rewards(solutions_filtered)  # ignore rewards
        winners_per_auction.append(winners)
        order_uids_settled.update(get_orders(winners))

    return winners_per_auction