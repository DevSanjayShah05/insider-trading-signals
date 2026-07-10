import type { InsiderTransaction } from "../types";
import { fmtDate, fmtShares, fmtUsd } from "../format";

export default function InsiderList({ insiders }: { insiders: InsiderTransaction[] }) {
  return (
    <div className="insider-list">
      {insiders.map((ins) => (
        <div className="insider-row" key={`${ins.name}-${ins.first_trans_date}`}>
          <span className="nm">
            {ins.name}
            {ins.title ? <span className="role"> — {ins.title}</span> : <span className="role"> — {ins.relationship}</span>}
          </span>
          <span className="mut" style={{ fontSize: 11 }}>
            {fmtShares(ins.shares)} sh @ ${ins.avg_price_per_share.toFixed(2)} · {fmtDate(ins.first_trans_date)}
            {ins.num_transactions > 1 ? ` (${ins.num_transactions} txns)` : ""}
          </span>
          <span className="val">{fmtUsd(ins.value_usd)}</span>
        </div>
      ))}
    </div>
  );
}
