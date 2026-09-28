import 'package:flutter/material.dart';

import '../../../core/theme/app_theme.dart';
import '../models/report.dart';

/// Icône et couleur par famille de document. Les familles se distinguent
/// d'abord par leur icône : la couleur seule ne suffit pas, notamment
/// pour les personnes qui distinguent mal les teintes.
class DocumentStyle {
  const DocumentStyle(this.icon, this.color);

  final IconData icon;
  final Color color;

  static DocumentStyle of(DocumentType type) {
    switch (type) {
      case DocumentType.cni:
        return const DocumentStyle(Icons.badge_outlined, AppTheme.primary);
      case DocumentType.permis:
        return const DocumentStyle(Icons.directions_car_outlined, AppTheme.accent);
      case DocumentType.passeport:
        return const DocumentStyle(Icons.flight_takeoff_outlined, AppTheme.success);
      case DocumentType.carteEtudiant:
        return const DocumentStyle(Icons.school_outlined, Color(0xFF6B4E9B));
      case DocumentType.carteConsulaire:
        return const DocumentStyle(Icons.public_outlined, Color(0xFF1E6F8F));
      case DocumentType.autre:
        return const DocumentStyle(Icons.folder_outlined, AppTheme.inkSoft);
    }
  }
}