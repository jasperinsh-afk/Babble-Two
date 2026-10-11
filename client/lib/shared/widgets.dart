import 'package:flutter/material.dart';

import '../app/theme.dart';
import 'models.dart';

/// 通用加载态
class LoadingView extends StatelessWidget {
  const LoadingView({super.key});

  @override
  Widget build(BuildContext context) =>
      const Center(child: CircularProgressIndicator());
}

/// 空态
class EmptyView extends StatelessWidget {
  const EmptyView({super.key, required this.text, this.icon = Icons.inbox_outlined});

  final String text;
  final IconData icon;

  @override
  Widget build(BuildContext context) => Center(
        child: Padding(
          padding: const EdgeInsets.all(40),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(icon, size: 56, color: GoQDColors.textSecondary.withValues(alpha: 0.5)),
              const SizedBox(height: 12),
              Text(text, style: const TextStyle(color: GoQDColors.textSecondary)),
            ],
          ),
        ),
      );
}

/// 错误态 + 重试
class ErrorView extends StatelessWidget {
  const ErrorView({super.key, required this.message, this.onRetry});

  final String message;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) => Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.wifi_off, size: 48, color: GoQDColors.textSecondary),
              const SizedBox(height: 12),
              Text(message, textAlign: TextAlign.center,
                  style: const TextStyle(color: GoQDColors.textSecondary)),
              if (onRetry != null) ...[
                const SizedBox(height: 16),
                OutlinedButton.icon(
                  onPressed: onRetry,
                  icon: const Icon(Icons.refresh),
                  label: const Text('重试'),
                ),
              ],
            ],
          ),
        ),
      );
}

/// 类型标签
class TagChip extends StatelessWidget {
  const TagChip({super.key, required this.text, this.color});

  final String text;
  final Color? color;

  @override
  Widget build(BuildContext context) {
    final c = color ?? GoQDColors.primary;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: c.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(6),
      ),
      child: Text(text, style: TextStyle(fontSize: 11, color: c, fontWeight: FontWeight.w600)),
    );
  }
}

/// 投票卡片（列表用）
class PollCard extends StatelessWidget {
  const PollCard({super.key, required this.poll, required this.onTap});

  final Poll poll;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final top = poll.options.isNotEmpty
        ? poll.options.reduce((a, b) => a.voteCount >= b.voteCount ? a : b)
        : null;

    return Card(
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  TagChip(text: poll.type.label),
                  if (poll.tag != null) ...[
                    const SizedBox(width: 6),
                    TagChip(text: poll.tag!.label, color: GoQDColors.accent),
                  ],
                  const Spacer(),
                  if (poll.hasVoted)
                    const Icon(Icons.check_circle, size: 16, color: GoQDColors.accent),
                  if (poll.remainingText.isNotEmpty) ...[
                    const SizedBox(width: 4),
                    Text(poll.remainingText,
                        style: const TextStyle(fontSize: 11, color: GoQDColors.textSecondary)),
                  ],
                ],
              ),
              const SizedBox(height: 10),
              Text(poll.title,
                  style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
              if (poll.description != null && poll.description!.isNotEmpty) ...[
                const SizedBox(height: 6),
                Text(poll.description!,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontSize: 13, color: GoQDColors.textSecondary)),
              ],
              if (top != null) ...[
                const SizedBox(height: 12),
                ClipRRect(
                  borderRadius: BorderRadius.circular(4),
                  child: LinearProgressIndicator(
                    value: (top.percent / 100).clamp(0.0, 1.0),
                    minHeight: 6,
                    backgroundColor: GoQDColors.border,
                    valueColor: const AlwaysStoppedAnimation(GoQDColors.primary),
                  ),
                ),
                const SizedBox(height: 6),
                Text('领先：${top.label} · ${top.percent.toStringAsFixed(1)}%',
                    style: const TextStyle(fontSize: 12, color: GoQDColors.textSecondary)),
              ],
              const SizedBox(height: 8),
              Text('${poll.totalVotes} 人已参与',
                  style: const TextStyle(fontSize: 12, color: GoQDColors.textSecondary)),
            ],
          ),
        ),
      ),
    );
  }
}

/// 社团卡片
class ClubCard extends StatelessWidget {
  const ClubCard({super.key, required this.club, required this.onTap});

  final Club club;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Card(
        child: ListTile(
          onTap: onTap,
          contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          leading: CircleAvatar(
            backgroundColor: GoQDColors.primary.withValues(alpha: 0.12),
            child: Text(club.name.substring(0, 1),
                style: const TextStyle(color: GoQDColors.primary, fontWeight: FontWeight.w700)),
          ),
          title: Row(
            children: [
              Flexible(child: Text(club.name, overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontWeight: FontWeight.w600))),
              if (club.isVerified) ...[
                const SizedBox(width: 4),
                const Icon(Icons.verified, size: 15, color: GoQDColors.primary),
              ],
            ],
          ),
          subtitle: Text('${club.category.label} · ${club.memberCount} 成员 · 热度 ${club.heatScore}',
              style: const TextStyle(fontSize: 12)),
          trailing: club.isMember
              ? const TagChip(text: '已加入', color: GoQDColors.accent)
              : null,
        ),
      );
}

/// 活动卡片
class EventCard extends StatelessWidget {
  const EventCard({super.key, required this.event, this.onTap, this.onJoin});

  final Event event;
  final VoidCallback? onTap;
  final VoidCallback? onJoin;

  @override
  Widget build(BuildContext context) => Card(
        child: ListTile(
          onTap: onTap,
          contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          title: Text(event.title, style: const TextStyle(fontWeight: FontWeight.w600)),
          subtitle: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const SizedBox(height: 4),
              Text('${_fmt(event.startAt)} · ${event.location ?? '待定'}',
                  style: const TextStyle(fontSize: 12)),
              const SizedBox(height: 2),
              Text(
                event.maxParticipants == null
                    ? '不限人数'
                    : '${event.participantCount}/${event.maxParticipants} 人',
                style: const TextStyle(fontSize: 12, color: GoQDColors.textSecondary),
              ),
            ],
          ),
          trailing: event.registeredByMe
              ? const TagChip(text: '已报名', color: GoQDColors.accent)
              : (event.isFull
                  ? const TagChip(text: '已满', color: GoQDColors.danger)
                  : (onJoin == null
                      ? null
                      : FilledButton(
                          onPressed: onJoin,
                          style: FilledButton.styleFrom(
                            minimumSize: const Size(64, 34),
                            padding: const EdgeInsets.symmetric(horizontal: 12),
                          ),
                          child: const Text('报名', style: TextStyle(fontSize: 13)),
                        ))),
        ),
      );

  static String _fmt(DateTime? d) {
    if (d == null) return '待定';
    return '${d.month}月${d.day}日 ${d.hour.toString().padLeft(2, '0')}:${d.minute.toString().padLeft(2, '0')}';
  }
}

/// 分区标题
class SectionHeader extends StatelessWidget {
  const SectionHeader({super.key, required this.title, this.action, this.onAction});

  final String title;
  final String? action;
  final VoidCallback? onAction;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.fromLTRB(16, 18, 8, 6),
        child: Row(
          children: [
            Text(title, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700)),
            const Spacer(),
            if (action != null)
              TextButton(onPressed: onAction, child: Text(action!)),
          ],
        ),
      );
}
