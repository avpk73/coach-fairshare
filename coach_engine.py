# coach_engine.py
import pandas as pd


class CoachFairShareEngine:
    """
    Mathematical Logic for Coach Fair-Share.
    This file can be used by Streamlit, a Mobile App API, or an Excel Processor.
    """

    def __init__(self, city_data, player_names, attendance_df, strategy):
        self.city_data = city_data
        self.city_names = [c['name'] for c in city_data]
        self.player_names = player_names
        self.attendance_df = attendance_df
        self.strategy = strategy
        self.num_cities = len(city_data)

    def calculate_settlement(self):
        # 1. Block Identification
        block_ids = []
        curr_block = 1
        for i in range(self.num_cities):
            if i > 0 and self.city_data[i]['M'] > 0:
                curr_block += 1
            block_ids.append(curr_block)

        unique_blocks = sorted(list(set(block_ids)))

        # 2. Block Unions
        block_unions = {}
        for b_id in unique_blocks:
            cities_in_block = [self.city_names[i]
                               for i, bid in enumerate(block_ids) if bid == b_id]
            union_mask = self.attendance_df[cities_in_block].any(axis=1)
            block_unions[b_id] = union_mask[union_mask].index.tolist()

        # 3. SLC Calculation
        slc_per_block = {}
        for b_id in unique_blocks:
            idxs = [i for i, bid in enumerate(block_ids) if bid == b_id]
            u_val = self.city_data[idxs[0]]['U']
            d_val = self.city_data[idxs[-1]]['D']
            size = len(block_unions[b_id])
            slc_per_block[b_id] = (u_val + d_val) / size if size > 0 else 0

        # 4. Initial Billing
        final_bills = {name: 0.0 for name in self.player_names}
        for name in self.player_names:
            for b_id in unique_blocks:
                if name in block_unions[b_id]:
                    final_bills[name] += slc_per_block[b_id]

        # 5. Link Efficiency
        savings_log = []
        for i in range(1, self.num_cities):
            p_b, c_b = block_ids[i-1], block_ids[i]
            if p_b != c_b:
                d_prev, u_curr, m_actual = self.city_data[i -
                                                          1]['D'], self.city_data[i]['U'], self.city_data[i]['M']
                saving = (d_prev + u_curr) - m_actual
                denom = d_prev + u_curr
                w_exit = d_prev / denom if denom > 0 else 0.5
                w_entry = u_curr / denom if denom > 0 else 0.5

                if saving > 0:
                    for p in block_unions[p_b]:
                        final_bills[p] -= (saving * w_exit) / \
                            len(block_unions[p_b])
                    for p in block_unions[c_b]:
                        final_bills[p] -= (saving * w_entry) / \
                            len(block_unions[c_b])
                    savings_log.append(
                        {"Route": f"{self.city_names[i-1]} → {self.city_names[i]}", "Type": "Saving", "Amount": saving})
                elif saving < 0:
                    loss = abs(saving)
                    bridgers = [p for p in block_unions[p_b]
                                if p in block_unions[c_b]]
                    target = bridgers if (
                        self.strategy != "Current Participants" and bridgers) else block_unions[c_b]
                    for p in target:
                        final_bills[p] += loss / len(target)
                    savings_log.append(
                        {"Route": f"{self.city_names[i-1]} → {self.city_names[i]}", "Type": "Loss", "Amount": -loss})

        # 6. Summation Integrity
        total_collected = sum(final_bills.values())
        last_city_idx = max([i for i in range(
            self.num_cities) if self.attendance_df[self.city_names[i]].any()] or [0])
        invoice_cost = self.city_data[0]['U'] + sum(
            c['M'] for c in self.city_data[1:last_city_idx+1]) + self.city_data[last_city_idx]['D']

        return {
            "final_bills": final_bills,
            "total_collected": total_collected,
            "invoice_cost": invoice_cost,
            "savings_log": savings_log,
            "block_info": [{"Block": b_id, "Route": " → ".join([self.city_names[i] for i, bid in enumerate(block_ids) if bid == b_id]), "Union Size": len(block_unions[b_id])} for b_id in unique_blocks]
        }
