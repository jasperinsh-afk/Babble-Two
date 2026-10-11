import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/theme.dart';
import '../../core/api/api_service.dart';
import 'auth_provider.dart';

class LoginPage extends ConsumerStatefulWidget {
  const LoginPage({super.key});

  @override
  ConsumerState<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends ConsumerState<LoginPage> {
  final _formKey = GlobalKey<FormState>();
  final _sid = TextEditingController(text: '20240001');
  final _pwd = TextEditingController(text: 'goqd1234');
  bool _loading = false;
  String? _error;
  bool _obscure = true;

  @override
  void dispose() {
    _sid.dispose();
    _pwd.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() {
      _loading = true;
      _error = null;
    });
    final ok = await ref
        .read(authStateProvider)
        .login(_sid.text.trim(), _pwd.text.trim());
    if (!mounted) return;
    setState(() => _loading = false);
    if (ok) {
      context.go('/home');
    } else {
      setState(() => _error = ref.read(authStateProvider).error ?? '登录失败');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.white,
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(28),
          child: Form(
            key: _formKey,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const SizedBox(height: 60),
                const Text('七德通',
                    style: TextStyle(fontSize: 32, fontWeight: FontWeight.w800,
                        color: GoQDColors.primary)),
                const SizedBox(height: 6),
                const Text('碰一碰，发现校园新鲜事',
                    style: TextStyle(fontSize: 14, color: GoQDColors.textSecondary)),
                const SizedBox(height: 48),
                TextFormField(
                  controller: _sid,
                  keyboardType: TextInputType.number,
                  decoration: const InputDecoration(
                    labelText: '学号', prefixIcon: Icon(Icons.badge_outlined)),
                  validator: (v) =>
                      (v == null || v.trim().isEmpty) ? '请输入学号' : null,
                ),
                const SizedBox(height: 14),
                TextFormField(
                  controller: _pwd,
                  obscureText: _obscure,
                  decoration: InputDecoration(
                    labelText: '密码',
                    prefixIcon: const Icon(Icons.lock_outline),
                    suffixIcon: IconButton(
                      icon: Icon(_obscure ? Icons.visibility_off : Icons.visibility),
                      onPressed: () => setState(() => _obscure = !_obscure),
                    ),
                  ),
                  validator: (v) =>
                      (v == null || v.length < 8) ? '密码至少 8 位' : null,
                ),
                if (_error != null) ...[
                  const SizedBox(height: 12),
                  Text(_error!, style: const TextStyle(color: GoQDColors.danger, fontSize: 13)),
                ],
                const SizedBox(height: 24),
                FilledButton(
                  onPressed: _loading ? null : _submit,
                  child: _loading
                      ? const SizedBox(height: 20, width: 20,
                          child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                      : const Text('登录'),
                ),
                const SizedBox(height: 12),
                TextButton(
                  onPressed: () => context.push('/register'),
                  child: const Text('还没有账号？用学校邮箱注册'),
                ),
                const SizedBox(height: 28),
                OutlinedButton.icon(
                  onPressed: () async {
                    try {
                      await ApiService.homeFeed();
                      if (mounted) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(content: Text('后端连接正常')),
                        );
                      }
                    } catch (e) {
                      if (mounted) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(content: Text('后端不可达：$e')),
                        );
                      }
                    }
                  },
                  icon: const Icon(Icons.wifi_tethering, size: 18),
                  label: const Text('检测后端连接'),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
