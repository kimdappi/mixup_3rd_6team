import { MessageCircle } from 'lucide-react';

export default function ConversationalBox({
  title = '한 줄로 말하면',
  children,
  tone = 'primary',
}) {
  const toneCls = {
    primary: 'bg-primary/8 border-primary/20 text-text',
    warning: 'bg-warning/10 border-warning/30 text-text',
    danger: 'bg-danger/10 border-danger/30 text-text',
    bonus: 'bg-bonus/10 border-bonus/30 text-text',
  }[tone] || 'bg-primary/8 border-primary/20 text-text';

  return (
    <div className={`relative rounded-2xl border ${toneCls} px-5 py-5 shadow-card`}>
      <div className="flex items-center gap-2 text-subtext text-sm font-medium mb-2">
        <MessageCircle className="w-4 h-4" />
        <span>💬 {title}</span>
      </div>
      <div className="text-text text-lg leading-relaxed font-medium whitespace-pre-line">
        {children}
      </div>
    </div>
  );
}
