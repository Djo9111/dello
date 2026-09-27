enum ReportKind {
  lost('lost', 'Perdu'),
  found('found', 'Trouvé');

  const ReportKind(this.value, this.label);
  final String value;
  final String label;

  static ReportKind fromValue(String value) =>
      ReportKind.values.firstWhere((kind) => kind.value == value);
}

enum DocumentType {
  cni('cni', "Carte d'identité"),
  permis('permis', 'Permis de conduire'),
  passeport('passeport', 'Passeport'),
  carteEtudiant('carte_etudiant', 'Carte étudiant'),
  carteConsulaire('carte_consulaire', 'Carte consulaire'),
  autre('autre', 'Autre document');

  const DocumentType(this.value, this.label);
  final String value;
  final String label;

  static DocumentType fromValue(String value) => DocumentType.values
      .firstWhere((type) => type.value == value, orElse: () => DocumentType.autre);
}

enum ReportStatus {
  open('open', 'En recherche'),
  matched('matched', 'Correspondance trouvée'),
  closed('closed', 'Clôturé');

  const ReportStatus(this.value, this.label);
  final String value;
  final String label;

  static ReportStatus fromValue(String value) => ReportStatus.values
      .firstWhere((status) => status.value == value, orElse: () => ReportStatus.open);
}

/// Les régions sont écrites comme l'API les attend (sans accents).
const senegalRegions = <String>[
  'Dakar', 'Diourbel', 'Fatick', 'Kaffrine', 'Kaolack', 'Kedougou',
  'Kolda', 'Louga', 'Matam', 'Saint-Louis', 'Sedhiou', 'Tambacounda',
  'Thies', 'Ziguinchor',
];

class Report {
  const Report({
    required this.id,
    required this.kind,
    required this.documentType,
    required this.region,
    required this.status,
    required this.createdAt,
    this.ownerNameMasked,
    this.commune,
    this.occurredOn,
    this.placeDetail,
    this.isPublished,
    this.hasDocumentNumber,
  });

  final String id;
  final ReportKind kind;
  final DocumentType documentType;
  final String region;
  final ReportStatus status;
  final DateTime createdAt;
  final String? ownerNameMasked;
  final String? commune;
  final DateTime? occurredOn;

  /// Champs présents uniquement dans la vue du propriétaire
  final String? placeDetail;
  final bool? isPublished;
  final bool? hasDocumentNumber;

  String get locationLabel =>
      commune == null || commune!.isEmpty ? region : '$commune, $region';

  factory Report.fromJson(Map<String, dynamic> json) {
    return Report(
      id: json['id'] as String,
      kind: ReportKind.fromValue(json['kind'] as String),
      documentType: DocumentType.fromValue(json['document_type'] as String),
      region: json['region'] as String,
      status: ReportStatus.fromValue(json['status'] as String),
      createdAt: DateTime.parse(json['created_at'] as String),
      ownerNameMasked: json['owner_name_masked'] as String?,
      commune: json['commune'] as String?,
      occurredOn: json['occurred_on'] == null
          ? null
          : DateTime.parse(json['occurred_on'] as String),
      placeDetail: json['place_detail'] as String?,
      isPublished: json['is_published'] as bool?,
      hasDocumentNumber: json['has_document_number'] as bool?,
    );
  }
}