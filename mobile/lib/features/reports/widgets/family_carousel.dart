import 'dart:async';

import 'package:flutter/material.dart';

import '../models/report.dart';
import 'report_tile.dart';

/// Carrousel d'une famille de documents.
///
/// Défile seul toutes les 4 secondes, et s'arrête définitivement dès que
/// l'utilisateur touche l'écran : reprendre la main pendant qu'il lit
/// serait pénible.
class FamilyCarousel extends StatefulWidget {
  const FamilyCarousel({
    super.key,
    required this.reports,
    required this.onReportTap,
  });

  final List<Report> reports;
  final void Function(Report) onReportTap;

  @override
  State<FamilyCarousel> createState() => _FamilyCarouselState();
}

class _FamilyCarouselState extends State<FamilyCarousel> {
  final _controller = PageController(viewportFraction: 0.82);

  Timer? _timer;
  int _page = 0;

  @override
  void initState() {
    super.initState();
    if (widget.reports.length > 1) _startAutoScroll();
  }

  @override
  void dispose() {
    _timer?.cancel();
    _controller.dispose();
    super.dispose();
  }

  void _startAutoScroll() {
    _timer = Timer.periodic(const Duration(seconds: 4), (_) {
      if (!mounted || !_controller.hasClients) return;

      _page = (_page + 1) % widget.reports.length;
      _controller.animateToPage(
        _page,
        duration: const Duration(milliseconds: 600),
        curve: Curves.easeInOut,
      );
    });
  }

  void _stopAutoScroll() {
    _timer?.cancel();
    _timer = null;
  }

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 170,
      child: Listener(
        onPointerDown: (_) => _stopAutoScroll(),
        child: PageView.builder(
          controller: _controller,
          itemCount: widget.reports.length,
          onPageChanged: (index) => _page = index,
          padEnds: false,
          itemBuilder: (context, index) {
            final report = widget.reports[index];
            return Padding(
              padding: const EdgeInsets.only(right: 12),
              child: ReportCarouselCard(
                report: report,
                onTap: () => widget.onReportTap(report),
              ),
            );
          },
        ),
      ),
    );
  }
}