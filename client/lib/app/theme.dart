import 'package:flutter/material.dart';

/// 七德通 GoQD 设计令牌
class GoQDColors {
  // 品牌主色（紫）
  static const primary = Color(0xFF6C4BF6);
  static const primaryLight = Color(0xFFA878FF);
  static const primaryDark = Color(0xFF4B2FD1);

  // 辅助色
  static const accent = Color(0xFF12A150);
  static const warning = Color(0xFFD98008);
  static const danger = Color(0xFFE5484D);

  // 中性
  static const bg = Color(0xFFF5F6FA);
  static const surface = Colors.white;
  static const border = Color(0xFFECECF3);
  static const textPrimary = Color(0xFF2D2D3A);
  static const textSecondary = Color(0xFF8A8AA0);

  // 投票类型色
  static const List<Color> chartPalette = [
    Color(0xFF6C4BF6),
    Color(0xFF12A150),
    Color(0xFFD98008),
    Color(0xFFE5484D),
    Color(0xFF0090FF),
    Color(0xFFA878FF),
  ];
}

class GoQDTheme {
  static ThemeData light() {
    final base = ThemeData(
      useMaterial3: true,
      colorScheme: ColorScheme.fromSeed(
        seedColor: GoQDColors.primary,
        brightness: Brightness.light,
        surface: GoQDColors.surface,
      ),
      scaffoldBackgroundColor: GoQDColors.bg,
      fontFamily: null,
    );

    return base.copyWith(
      appBarTheme: const AppBarTheme(
        backgroundColor: Colors.white,
        foregroundColor: GoQDColors.textPrimary,
        elevation: 0,
        centerTitle: true,
        titleTextStyle: TextStyle(
          fontSize: 17,
          fontWeight: FontWeight.w600,
          color: GoQDColors.textPrimary,
        ),
      ),
      cardTheme: CardThemeData(
        color: Colors.white,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
          side: const BorderSide(color: GoQDColors.border),
        ),
        margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: GoQDColors.primary,
          foregroundColor: Colors.white,
          elevation: 0,
          minimumSize: const Size.fromHeight(48),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
          textStyle: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: GoQDColors.primary,
          minimumSize: const Size.fromHeight(48),
          side: const BorderSide(color: GoQDColors.primary),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: Colors.white,
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: GoQDColors.border),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: GoQDColors.border),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: GoQDColors.primary, width: 1.5),
        ),
      ),
      bottomNavigationBarTheme: const BottomNavigationBarThemeData(
        backgroundColor: Colors.white,
        selectedItemColor: GoQDColors.primary,
        unselectedItemColor: GoQDColors.textSecondary,
        type: BottomNavigationBarType.fixed,
        elevation: 0,
      ),
      chipTheme: ChipThemeData(
        backgroundColor: Colors.white,
        selectedColor: GoQDColors.primary,
        labelStyle: const TextStyle(fontSize: 13),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
        side: const BorderSide(color: GoQDColors.border),
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      ),
      dividerTheme: const DividerThemeData(color: GoQDColors.border, thickness: 1),
    );
  }
}
