import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../app/theme.dart';
import '../../core/api/api_service.dart';
import '../../shared/models.dart';
import '../../shared/widgets.dart';

/// 社团广场（PRD §3.2 C-201 ~ C-203）
class ClubPage extends StatefulWidget {
  const ClubPage({super.key});

  @override
  State<ClubPage> createState() => _ClubPageState();
}

class _ClubPageState extends State<ClubPage> {
  List<Club> _items = [];
  ClubCategory? _category;
  bool _loading = true;
  String? _error;
  final _search = TextEditingController();

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _search.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final page = await ApiService.clubList(
        category: _category?.name,
        keyword: _search.text.trim(),
      );
      setState(() => _items = page.items);
    } catch (e) {
      setState(() => _error = e.toString());
    }
    if (mounted) setState(() => _loading = false);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('社团广场')),
      body: RefreshIndicator(
        onRefresh: _load,
        child: ListView(
          padding: const EdgeInsets.only(bottom: 24),
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
              child: TextField(
                controller: _search,
                textInputAction: TextInputAction.search,
                onSubmitted: (_) => _load(),
                decoration: InputDecoration(
                  hintText: '搜索社团',
                  prefixIcon: const Icon(Icons.search, size: 20),
                  suffixIcon: IconButton(
                    icon: const Icon(Icons.clear, size: 18),
                    onPressed: () {
                      _search.clear();
                      _load();
                    },
                  ),
                ),
              ),
            ),
            SizedBox(
              height: 40,
              child: ListView(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                scrollDirection: Axis.horizontal,
                children: [
                  _CateChip(label: '全部', selected: _category == null,
                      onTap: () { setState(() => _category = null); _load(); }),
                  const SizedBox(width: 8),
                  for (final c in ClubCategory.values) ...[
                    _CateChip(label: c.label, selected: _category == c,
                        onTap: () { setState(() => _category = c); _load(); }),
                    const SizedBox(width: 8),
                  ],
                ],
              ),
            ),
            if (_loading)
              const SizedBox(height: 260, child: LoadingView())
            else if (_error != null)
              SizedBox(height: 260, child: ErrorView(message: _error!, onRetry: _load))
            else if (_items.isEmpty)
              const SizedBox(height: 260, child: EmptyView(text: '暂无社团'))
            else
              for (final c in _items)
                ClubCard(club: c, onTap: () => context.push('/club/${c.id}')),
          ],
        ),
      ),
    );
  }
}

class _CateChip extends StatelessWidget {
  const _CateChip({required this.label, required this.selected, required this.onTap});

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
