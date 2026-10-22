import { Badge } from "./ui.jsx";
import { ACTIONS, describeLog } from "../utils/activity.js";
import { dateTime, timeAgo } from "../utils/format.js";

// Newest-first list of audit entries, written in plain English.
export default function ActivityList({ logs, productNames, compact = false }) {
  return (
    <ol className={`activity ${compact ? "activity-compact" : ""}`}>
      {logs.map((log) => {
        const action = ACTIONS[log.action_type] || { label: log.action_type, tone: "neutral" };
        return (
          <li key={log.id} className="activity-item">
            <span className={`dot dot-${action.tone}`} aria-hidden="true" />
            <div className="activity-main">
              <div className="activity-top">
                <Badge tone={action.tone}>{action.label}</Badge>
                <span className="muted small" title={dateTime(log.timestamp)}>
                  {compact ? timeAgo(log.timestamp) : dateTime(log.timestamp)}
                </span>
              </div>
              <p>{describeLog(log, productNames[log.product_id])}</p>
              <span className="muted small">By {log.actor}</span>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
