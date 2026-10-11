import 'package:flutter/material.dart';
import 'package:table_calendar/table_calendar.dart';

import '../../app/theme.dart';
import '../../core/api/api_service.dart';
import '../../shared/models.dart';
import '../../shared/widgets.dart';

/// 活动日历（PRD §3.3 E-001 ~ E-005）
class CalendarPage extends StatefulWidget {
  const CalendarPage({super.key});

  @override
  State<CalendarPage> createState() => _CalendarPageState();
}

class _CalendarPageState extends State<CalendarPage> {
  DateTime _focused = DateTime.now();
  DateTime _selected = DateTime.now();
  Map<DateTime, List<Event>> _events = {};
  List<Event> _upcoming = [];
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
      final days = await ApiService.calendar(_focused.year, _focused.month);
      final map = <DateTime, List<Event>>{};
      for (final d in days) {
        final key = DateTime(d.date.year, d.date.month, d.date.day);
        map[key] = d.events;
      }
      final all = await ApiService.eventList(start: DateTime.now());
      setState(() {
        _events = map;
        _upcoming = all.items;
      });
    } catch (e) {
      setState(() => _error = e.toString());
    }
    if (mounted) setState(() => _loading = false);
  }

  List<Event> _eventsFor(DateTime day) =>
      _events[DateTime(day.year, day.month, day.day)] ?? const [];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('活动日历'),
        actions: [
          IconButton(icon: const Icon(Icons.refresh), onPressed: _load),
        ],
      ),
      body: _loading
          ? const LoadingView()
          : (_error != null
              ? ErrorView(message: _error!, onRetry: _load)
              : RefreshIndicator(
                  onRefresh: _load,
                  child: ListView(
                    padding: const EdgeInsets.only(bottom: 32),
                    children: [
                      Card(
                        margin: const EdgeInsets.all(16),
                        child: Padding(
                          padding: const EdgeInsets.all(8),
                          child: TableCalendar<Event>(
                            firstDay: DateTime.now().subtract(const Duration(days: 365)),
                            lastDay: DateTime.now().add(const Duration(days: 365)),
                            focusedDay: _focused,
                            selectedDayPredicate: (d) => isSameDay(d, _selected),
                            eventLoader: _eventsFor,
                            calendarFormat: CalendarFormat.month,
                            availableCalendarFormats: const {
                              CalendarFormat.month: '月',
                              CalendarFormat.week: '周',
                              CalendarFormat.twoWeeks: '双周',
                            },
                            headerStyle: const HeaderStyle(
                              formatButtonShowsNext: false,
                              titleCentered: true,
                            ),
                            calendarStyle: const CalendarStyle(
                              todayDecoration: BoxDecoration(
                                  color: GoQDColors.primaryLight, shape: BoxShape.circle),
                              selectedDecoration: BoxDecoration(
                                  color: GoQDColors.primary, shape: BoxShape.circle),
                              markerDecoration: BoxDecoration(
                                  color: GoQDColors.accent, shape: BoxShape.circle),
                            ),
                            onDaySelected: (sel, foc) {
                              setState(() {
                                _selected = sel;
                                _focused = foc;
                              });
                            },
                            onPageChanged: (foc) {
                              setState(() => _focused = foc);
                              _load();
                            },
                          ),
                        ),
                      ),
                      SectionHeader(
                        title:
                            '${_selected.month}月${_selected.day}日 · ${_eventsFor(_selected).length} 场活动',
                      ),
                      for (final e in _eventsFor(_selected))
                        EventCard(
                          event: e,
                          onJoin: () async {
                            await ApiService.joinEvent(e.id);
                            await _load();
                          },
                        ),
                      const SectionHeader(title: '即将开始'),
                      if (_upcoming.isEmpty)
                        const Padding(
                          padding: EdgeInsets.all(24),
                          child: Center(
                              child: Text('暂无活动',
                                  style: TextStyle(color: GoQDColors.textSecondary))),
                        )
                      else
                        for (final e in _upcoming)
                          EventCard(
                            event: e,
                            onJoin: () async {
                              await ApiService.joinEvent(e.id);
                              await _load();
                            },
                          ),
                    ],
                  ),
                )),
    );
  }
}
