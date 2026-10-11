import 'package:flutter/material.dart';

import '../../app/theme.dart';
import '../../core/api/api_service.dart';
import '../../shared/models.dart';
import '../../shared/widgets.dart';

/// 社团主页 + 内容流（PRD §3.2 C-101 ~ C-106）
class ClubDetailPage extends StatefulWidget {
  const ClubDetailPage({super.key, required this.clubId});

  final int clubId;

  @override
  State<ClubDetailPage> createState() => _ClubDetailPageState();
}

class _ClubDetailPageState extends State<ClubDetailPage> {
  Club? _club;
  List<ClubPost> _posts = [];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final club = await ApiService.clubDetail(widget.clubId);
      final posts = await ApiService.clubPosts(widget.clubId);
      setState(() {
        _club = club;
        _posts = posts.items;
      });
    } catch (e) {
      setState(() => _error = e.toString());
    }
    if (mounted) setState(() => _loading = false);
  }

  Future<void> _toggleJoin() async {
    final club = _club;
    if (club == null) return;
    try {
      if (club.isMember) {
        await ApiService.leaveClub(club.id);
      } else {
        await ApiService.joinClub(club.id);
      }
      await _load();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(club.isMember ? '已退出社团' : '已加入社团')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text('操作失败：$e')));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final club = _club;
    return Scaffold(
      appBar: AppBar(title: Text(club?.name ?? '社团')),
      body: _loading
          ? const LoadingView()
          : (_error != null
              ? ErrorView(message: _error!, onRetry: _load)
              : club == null
                  ? const EmptyView(text: '社团不存在')
                  : RefreshIndicator(
                      onRefresh: _load,
                      child: ListView(
                        padding: const EdgeInsets.only(bottom: 32),
                        children: [
                          Container(
                            padding: const EdgeInsets.all(20),
                            color: Colors.white,
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  children: [
                                    CircleAvatar(
                                      radius: 30,
                                      backgroundColor:
                                          GoQDColors.primary.withValues(alpha: 0.12),
                                      child: Text(club.name.substring(0, 1),
                                          style: const TextStyle(
                                              color: GoQDColors.primary,
                                              fontSize: 22,
                                              fontWeight: FontWeight.w700)),
                                    ),
                                    const SizedBox(width: 14),
                                    Expanded(
                                      child: Column(
                                        crossAxisAlignment: CrossAxisAlignment.start,
                                        children: [
                                          Row(
                                            children: [
                                              Flexible(
                                                child: Text(club.name,
                                                    overflow: TextOverflow.ellipsis,
                                                    style: const TextStyle(
                                                        fontSize: 18,
                                                        fontWeight: FontWeight.w700)),
                                              ),
                                              if (club.isVerified) ...[
                                                const SizedBox(width: 4),
                                                const Icon(Icons.verified, size: 16,
                                                    color: GoQDColors.primary),
                                              ],
                                            ],
                                          ),
                                          const SizedBox(height: 4),
                                          Text(
                                            '${club.category.label} · ${club.memberCount} 成员 · 热度 ${club.heatScore}',
                                            style: const TextStyle(
                                                fontSize: 12,
                                                color: GoQDColors.textSecondary),
                                          ),
                                        ],
                                      ),
                                    ),
                                  ],
                                ),
                                if (club.description != null) ...[
                                  const SizedBox(height: 14),
                                  Text(club.description!,
                                      style: const TextStyle(
                                          fontSize: 14,
                                          height: 1.6,
                                          color: GoQDColors.textSecondary)),
                                ],
                                const SizedBox(height: 16),
                                SizedBox(
                                  width: double.infinity,
                                  child: club.isMember
                                      ? OutlinedButton(
                                          onPressed: _toggleJoin,
                                          child: const Text('退出社团'),
                                        )
                                      : FilledButton(
                                          onPressed: _toggleJoin,
                                          child: const Text('加入社团'),
                                        ),
                                ),
                              ],
                            ),
                          ),
                          const SectionHeader(title: '社团动态'),
                          if (_posts.isEmpty)
                            const Padding(
                              padding: EdgeInsets.all(24),
                              child: Center(
                                  child: Text('暂无动态',
                                      style: TextStyle(
                                          color: GoQDColors.textSecondary))),
                            )
                          else
                            for (final p in _posts) _PostTile(post: p),
                        ],
                      ),
                    )),
    );
  }
}

class _PostTile extends StatelessWidget {
  const _PostTile({required this.post});

  final ClubPost post;

  @override
  Widget build(BuildContext context) => Container(
        margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: GoQDColors.border),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (post.isPinned)
              const Padding(
                padding: EdgeInsets.only(bottom: 6),
                child: TagChip(text: '置顶', color: GoQDColors.warning),
              ),
            if (post.title != null)
              Text(post.title!,
                  style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
            const SizedBox(height: 6),
            Text(post.content,
                style: const TextStyle(fontSize: 14, height: 1.6)),
            const SizedBox(height: 10),
            Row(
              children: [
                const Icon(Icons.favorite_border, size: 15, color: GoQDColors.textSecondary),
                const SizedBox(width: 4),
                Text('${post.likeCount}',
                    style: const TextStyle(fontSize: 12, color: GoQDColors.textSecondary)),
                const SizedBox(width: 16),
                const Icon(Icons.mode_comment_outlined, size: 15,
                    color: GoQDColors.textSecondary),
                const SizedBox(width: 4),
                Text('${post.commentCount}',
                    style: const TextStyle(fontSize: 12, color: GoQDColors.textSecondary)),
              ],
            ),
          ],
        ),
      );
}
