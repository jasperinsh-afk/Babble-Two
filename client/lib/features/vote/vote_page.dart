import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../app/theme.dart';
import '../../core/api/api_service.dart';
import '../../shared/models.dart';
import '../../shared/widgets.dart';

/// 投票中心列表（PRD §3.1 V-201 ~ V-203）
class VotePage extends StatefulWidget {
  const VotePage({super.key});

  @override
  State<VotePage> createState() => _VotePageState();
}

class _VotePageState extends State<VotePage> {
  PollTag? _tag;
  List<Poll> _items = [];
  bool _loading = true;
  String? _error;
  int _offset = 0;
  bool _hasMore = true;
  final _scroll = ScrollController();

  @override
  void initState() {
    super.initState();
    _scroll.addListener(_onScroll);
    _load();
  }

  @override
  void dispose() {
    _scroll.dispose();
    super.dispose();
  }

  void _onScroll() {
    if (_scroll.position.pixels >= _scroll.position.maxScrollExtent - 200 &&
        !_loading &&
        _hasMore) {
      _loadMore();
    }
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
      _offset = 0;
    });
    try {
      final page = await ApiService.pollList(tag: _tag?.value);
      setState(() {
        _items = page.items;
        _hasMore = page.hasMore;
      });
    } catch (e) {
      setState(() => _error = e.toString());
    }
    if (mounted) setState(() => _loading = false);
  }

  Future<void> _loadMore() async {
    setState(() => _loading = true);
    try {
      final page = await ApiService.pollList(tag: _tag?.value, offset: _offset + 20);
      setState(() {
        _items.addAll(page.items);
        _offset += 20;
        _hasMore = page.hasMore;
      });
    } catch (_) {}
    if (mounted) setState(() => _loading = false);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('投票中心')),
      body: RefreshIndicator(
        onRefresh: _load,
        child: ListView(
          controller: _scroll,
          padding: const EdgeInsets.only(bottom: 24),
          children: [
            // 筛选标签（V-202）
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
              child: Wrap(
                spacing: 8,
                children: [
                  _FilterChip(
                    label: '全部',
                    selected: _tag == null,
                    onTap: () {
                      setState(() => _tag = null);
                      _load();
                    },
                  ),
                  for (final t in PollTag.values)
                    _FilterChip(
                      label: t.label,
                      selected: _tag == t,
                      onTap: () {
                        setState(() => _tag = t);
                        _load();
                      },
                    ),
                ],
              ),
            ),
            if (_loading && _items.isEmpty)
              const SizedBox(height: 300, child: LoadingView())
            else if (_error != null)
              SizedBox(height: 300, child: ErrorView(message: _error!, onRetry: _load))
            else if (_items.isEmpty)
              const SizedBox(height: 300, child: EmptyView(text: '暂无投票'))
            else
              for (final p in _items)
                PollCard(poll: p, onTap: () => context.push('/vote/${p.id}')),
            if (_loading && _items.isNotEmpty)
              const Padding(
                padding: EdgeInsets.all(16),
                child: Center(child: CircularProgressIndicator()),
              ),
          ],
        ),
      ),
    );
  }
}

class _FilterChip extends StatelessWidget {
  const _FilterChip({required this.label, required this.selected, required this.onTap});

  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => ChoiceChip(
        label: Text(label),
        selected: selected,
        onSelected: (_) => onTap(),
        showCheckmark: false,
        labelStyle: TextStyle(
          color: selected ? Colors.white : GoQDColors.textSecondary,
          fontWeight: selected ? FontWeight.w600 : FontWeight.normal,
        ),
        selectedColor: GoQDColors.primary,
        backgroundColor: Colors.white,
      );
}
