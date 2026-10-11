import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../features/auth/auth_provider.dart';
import '../features/auth/login_page.dart';
import '../features/auth/register_page.dart';
import '../features/calendar/calendar_page.dart';
import '../features/club/club_detail_page.dart';
import '../features/club/club_page.dart';
import '../features/home/home_page.dart';
import '../features/living/living_page.dart';
import '../features/nfc/nfc_page.dart';
import '../features/profile/profile_page.dart';
import '../features/vote/vote_detail_page.dart';
import '../features/vote/vote_page.dart';
import 'shell.dart';

final routerProvider = Provider<GoRouter>((ref) {
  final auth = ref.watch(authStateProvider);

  return GoRouter(
    initialLocation: '/home',
    debugLogDiagnostics: false,
    refreshListenable: auth,
    redirect: (context, state) {
      final loc = state.matchedLocation;
      final isAuthRoute =
          loc == '/login' || loc == '/register';
      if (auth.status == AuthStatus.unknown) return null;
      if (auth.status == AuthStatus.unauthenticated && !isAuthRoute) {
        return '/login';
      }
      if (auth.status == AuthStatus.authenticated && isAuthRoute) {
        return '/home';
      }
      return null;
    },
    routes: [
      GoRoute(path: '/login', builder: (_, __) => const LoginPage()),
      GoRoute(path: '/register', builder: (_, __) => const RegisterPage()),
      StatefulShellRoute.indexedStack(
        builder: (context, state, nav) => AppShell(navigationShell: nav),
        branches: [
          StatefulShellBranch(
            navigatorKey: GlobalKey<NavigatorState>(debugLabel: 'home'),
            routes: [
              GoRoute(
                path: '/home',
                builder: (_, __) => const HomePage(),
                routes: [
                  GoRoute(
                    path: 'vote/:id',
                    builder: (_, s) =>
                        VoteDetailPage(pollId: int.parse(s.pathParameters['id']!)),
                  ),
                  GoRoute(
                    path: 'club/:id',
                    builder: (_, s) =>
                        ClubDetailPage(clubId: int.parse(s.pathParameters['id']!)),
                  ),
                  GoRoute(
                    path: 'nfc',
                    builder: (_, __) => const NfcPage(),
                  ),
                ],
              ),
            ],
          ),
          StatefulShellBranch(
            navigatorKey: GlobalKey<NavigatorState>(debugLabel: 'vote'),
            routes: [
              GoRoute(
                path: '/vote',
                builder: (_, __) => const VotePage(),
                routes: [
                  GoRoute(
                    path: ':id',
                    builder: (_, s) =>
                        VoteDetailPage(pollId: int.parse(s.pathParameters['id']!)),
                  ),
                ],
              ),
            ],
          ),
          StatefulShellBranch(
            navigatorKey: GlobalKey<NavigatorState>(debugLabel: 'club'),
            routes: [
              GoRoute(
                path: '/club',
                builder: (_, __) => const ClubPage(),
                routes: [
                  GoRoute(
                    path: ':id',
                    builder: (_, s) =>
                        ClubDetailPage(clubId: int.parse(s.pathParameters['id']!)),
                  ),
                ],
              ),
            ],
          ),
          StatefulShellBranch(
            navigatorKey: GlobalKey<NavigatorState>(debugLabel: 'calendar'),
            routes: [
              GoRoute(path: '/calendar', builder: (_, __) => const CalendarPage()),
            ],
          ),
          StatefulShellBranch(
            navigatorKey: GlobalKey<NavigatorState>(debugLabel: 'profile'),
            routes: [
              GoRoute(path: '/profile', builder: (_, __) => const ProfilePage()),
            ],
          ),
        ],
      ),
      // 独立全屏路由（Deep Link 直达）
      GoRoute(
        path: '/nfc',
        builder: (_, __) => const NfcPage(),
      ),
      GoRoute(
        path: '/vote/:id',
        builder: (_, s) => VoteDetailPage(pollId: int.parse(s.pathParameters['id']!)),
      ),
      GoRoute(
        path: '/club/:id',
        builder: (_, s) => ClubDetailPage(clubId: int.parse(s.pathParameters['id']!)),
      ),
      GoRoute(
        path: '/living',
        builder: (_, __) => const LivingPage(),
      ),
    ],
  );
});
