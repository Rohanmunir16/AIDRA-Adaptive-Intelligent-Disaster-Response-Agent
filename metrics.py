class Metrics:

    def __init__(self):

        self.victims_saved = 0

        self.total_rescue_time = 0

        self.rescued_count = 0

        self.replanning_count = 0

        self.blocked_routes_count = 0

        self.ml_predictions_made = 0
        
        self.victims_dead = 0
        

    def avg_rescue_time(self):

        if self.rescued_count == 0:
            return 0

        return (
            self.total_rescue_time
            / self.rescued_count
        )
    
    def success_rate(self):

        total = self.victims_saved + self.victims_dead
    
        if total == 0:
            return 0
    
        return (
            self.victims_saved / total
        ) * 100