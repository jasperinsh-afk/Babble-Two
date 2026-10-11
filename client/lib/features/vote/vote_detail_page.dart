import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';

import '../../app/theme.dart';
import '../../core/api/api_service.dart';
import '../../core/network/api_client.dart';
import '../../shared/models.dart';
import '../../shared/widgets.dart';

/// 投票详情：投票 / 改票一次 / 实时结果饼图 / 立场短评 / 接龙
/// PRD §3.1 V-001 ~ V-006、V-101 ~ V-106
class VoteDetailPage extends StatefulWidget {
  const VoteDetailPage({super.key, required this.pollId});

  final int pollId;

  @override
  State<VoteDetailPage> createState() => _VoteDetailPageState();
}

class _VoteDetailPageState extends State<VoteDetailPage> {
  Poll? _poll;
  VoteResult? _result;
  List<PollComment> _comments = [];
  final Set<int> _selected = {};
  bool _loading = true;
  bool _submitting = false;
  String? _error;
  final _commentCtrl = TextEditingController();

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _commentCtrl.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final poll = await ApiService.pollDetail(widget.pollId);
      _selected
        ..clear()
        ..addAll(poll.myChoice ?? const []);
      setState(() => _poll = poll);
      final results = await ApiService.pollResults(widget.pollId);
      final comments = await ApiService.pollComments(widget.pollId);
      setState(() {
        _result = results;
        _comments = comments.items;
      });
    } catch (e) {
      setState(() => _error = e.toString());
    }
    if (mounted) setState(() => _loading = false);
  }

  Future<void> _submit() async {
    final poll = _poll;
    if (poll == null || _selected.isEmpty) return;
    setState(() => _submitting = true);
    try {
      final updated = await ApiService.castVote(
        poll.id,
        _selected.toList(),
        change: poll.hasVoted,
      );
      setState(() => _poll = updated);
      final r = await ApiService.pollResults(poll.id);
      setState(() => _result = r);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(poll.hasVoted ? '已修改投票' : '投票成功')),
        );
      }
    } on ApiException catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(e.message)));
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text('提交失败：$e')));
      }
    }
    if (mounted) setState(() => _submitting = false);
  }

  Future<void> _sendComment() async {
    final text = _commentCtrl.text.trim();
    if (text.isEmpty) return;
    try {
      final c = await ApiService.addComment(widget.pollId, text);
      setState(() {
        _comments.insert(0, c);
        _commentCtrl.clear();
      });
    } on ApiException catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(e.message)));
      }
    }
  }

  void _toggle(int id) {
    final poll = _poll!;
    if (poll.type == PollType.multi) {
      setState(() {
        if (_selected.contains(id)) {
          _selected.remove(id);
        } else {
          if (poll.maxChoices != null && _selected.length >= poll.maxChoices!) {
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(content: Text('最多可选 ${poll.maxChoices} 项')),
            );
            return;
          }
          _selected.add(id);
        }
      });
    } else {
      setState(() {
        _selected
          ..clear()
          ..add(id);
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final poll = _poll;
    return Scaffold(
      appBar: AppBar(title: const Text('投票详情')),
      body: _loading
          ? const LoadingView()
          : (_error != null
              ? ErrorView(message: _error!, onRetry: _load)
              : poll == null
                  ? const EmptyView(text: '投票不存在')
                  : _buildBody(poll)),
    );
  }

  Widget _buildBody(Poll poll) {
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 32),
        children: [
          Row(
            children: [
              TagChip(text: poll.type.label),
              if (poll.tag != null) ...[
                const SizedBox(width: 6),
                TagChip(text: poll.tag!.label, color: GoQDColors.accent),
              ],
              const Spacer(),
              Text(poll.remainingText,
                  style: const TextStyle(fontSize: 12, color: GoQDColors.textSecondary)),
            ],
          ),
          const SizedBox(height: 12),
          Text(poll.title,
              style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w700)),
          if (poll.description != null) ...[
            const SizedBox(height: 10),
            Text(poll.description!,
                style: const TextStyle(fontSize: 14, height: 1.6,
                    color: GoQDColors.textSecondary)),
          ],
          const SizedBox(height: 18),

          // 选项 / 结果
          if (poll.hasVoted || !poll.status.isOpen)
            _ResultView(result: _result)
          else
            _OptionsView(
              poll: poll,
              selected: _selected,
              onToggle: _toggle,
            ),

          const SizedBox(height: 18),

          // 投票按钮
          if (poll.status.isOpen && !poll.hasVoted)
            FilledButton(
              onPressed: _selected.isEmpty || _submitting ? null : _submit,
              child: _submitting
                  ? const SizedBox(height: 20, width: 20,
                      child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                  : const Text('提交投票'),
            ),
          if (poll.hasVoted && poll.allowChange && !poll.isChanged) ...[
            OutlinedButton(
              onPressed: _selected.isEmpty || _submitting ? null : _submit,
              child: const Text('修改投票（仅一次）'),
            ),
          ],
          if (poll.isChanged)
            const Padding(
              padding: EdgeInsets.only(top: 8),
              child: Center(
                child: Text('你已修改过一次，无法再次修改',
                    style: TextStyle(fontSize: 12, color: GoQDColors.textSecondary)),
              ),
            ),

          const SizedBox(height: 24),
          const Divider(),

          // 立场短评（V-005）
          SectionHeader(title: '立场短评', action: null),
          Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _commentCtrl,
                  maxLength: 200,
                  decoration: const InputDecoration(
                    hintText: '说说你的理由…',
                    isDense: true,
                  ),
                ),
              ),
              const SizedBox(width: 8),
              IconButton.filled(
                onPressed: _sendComment,
                icon: const Icon(Icons.send, size: 18),
              ),
            ],
          ),
          const SizedBox(height: 8),
          if (_comments.isEmpty)
            const Padding(
              padding: EdgeInsets.all(12),
              child: Text('还没有人发表立场',
                  style: TextStyle(fontSize: 13, color: GoQDColors.textSecondary)),
            )
          else
            for (final c in _comments) _CommentTile(comment: c),
        ],
      ),
    );
  }
}

class _OptionsView extends StatelessWidget {
  const _OptionsView({
    required this.poll,
    required this.selected,
    required this.onToggle,
  });

  final Poll poll;
  final Set<int> selected;
  final ValueChanged<int> onToggle;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        for (final o in poll.options)
          Padding(
            padding: const EdgeInsets.only(bottom: 10),
            child: Material(
              color: Colors.white,
              borderRadius: BorderRadius.circular(14),
              child: InkWell(
                borderRadius: BorderRadius.circular(14),
                onTap: () => onToggle(o.id),
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(
                      color: selected.contains(o.id)
                          ? GoQDColors.primary
                          : GoQDColors.border,
                      width: selected.contains(o.id) ? 1.6 : 1,
                    ),
                  ),
                  child: Row(
                    children: [
                      Icon(
                        selected.contains(o.id)
                            ? (poll.type == PollType.multi
                                ? Icons.check_box
                                : Icons.radio_button_checked)
                            : (poll.type == PollType.multi
                                ? Icons.check_box_outline_blank
                                : Icons.radio_button_unchecked),
                        color: selected.contains(o.id)
                            ? GoQDColors.primary
                            : GoQDColors.textSecondary,
                        size: 20,
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                          child: Text(o.label,
                              style: const TextStyle(fontSize: 15))),
                    ],
                  ),
                ),
              ),
            ),
          ),
      ],
    );
  }
}

class _ResultView extends StatelessWidget {
  const _ResultView({required this.result});

  final VoteResult? result;

  @override
  Widget build(BuildContext context) {
    if (result == null) return const SizedBox.shrink();
    final opts = result!.options;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            const Text('实时结果',
                style: TextStyle(fontSize: 15, fontWeight: FontWeight.w700)),
            const Spacer(),
            Text('共 ${result!.totalVotes} 票',
                style: const TextStyle(fontSize: 12, color: GoQDColors.textSecondary)),
          ],
        ),
        const SizedBox(height: 12),
        if (opts.length > 2)
          SizedBox(
            height: 180,
            child: PieChart(
              PieChartData(
                sectionsSpace: 2,
                centerSpaceRadius: 42,
                sections: [
                  for (var i = 0; i < opts.length; i++)
                    PieChartSectionData(
                      value: opts[i].percent,
                      title: '${opts[i].percent.toStringAsFixed(0)}%',
                      color: GoQDColors.chartPalette[i % GoQDColors.chartPalette.length],
                      radius: 52,
                      titleStyle: const TextStyle(
                          fontSize: 12, fontWeight: FontWeight.w700, color: Colors.white),
                    ),
                ],
              ),
            ),
          ),
        const SizedBox(height: 8),
        for (var i = 0; i < opts.length; i++)
          Padding(
            padding: const EdgeInsets.only(bottom: 12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Container(
                      width: 8,
                      height: 8,
                      decoration: BoxDecoration(
                        color: GoQDColors.chartPalette[i % GoQDColors.chartPalette.length],
                        shape: BoxShape.circle,
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(child: Text(opts[i].label, style: const TextStyle(fontSize: 14))),
                    Text('${opts[i].voteCount} 票',
                        style: const TextStyle(fontSize: 13, color: GoQDColors.textSecondary)),
                    const SizedBox(width: 8),
                    SizedBox(
                      width: 48,
                      child: Text('${opts[i].percent.toStringAsFixed(1)}%',
                          textAlign: TextAlign.right,
                          style: const TextStyle(
                              fontSize: 14, fontWeight: FontWeight.w700,
                              color: GoQDColors.primary)),
                    ),
                  ],
                ),
                const SizedBox(height: 6),
                ClipRRect(
                  borderRadius: BorderRadius.circular(4),
                  child: LinearProgressIndicator(
                    value: (opts[i].percent / 100).clamp(0.0, 1.0),
                    minHeight: 8,
                    backgroundColor: GoQDColors.border,
                    valueColor: AlwaysStoppedAnimation(
                        GoQDColors.chartPalette[i % GoQDColors.chartPalette.length]),
                  ),
                ),
              ],
            ),
          ),
      ],
    );
  }
}

class _CommentTile extends StatelessWidget {
  const _CommentTile({required this.comment});

  final PollComment comment;

  @override
  Widget build(BuildContext context) => Container(
        margin: const EdgeInsets.only(bottom: 10),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: GoQDColors.border),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Text(comment.authorNickname,
                    style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600)),
                const Spacer(),
                const Icon(Icons.favorite_border, size: 14, color: GoQDColors.textSecondary),
                const SizedBox(width: 4),
                Text('${comment.likeCount}',
                    style: const TextStyle(fontSize: 12, color: GoQDColors.textSecondary)),
              ],
            ),
            const SizedBox(height: 6),
            Text(comment.content, style: const TextStyle(fontSize: 14, height: 1.5)),
          ],
        ),
      );
}
