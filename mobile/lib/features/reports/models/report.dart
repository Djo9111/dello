enum ReportKind {
  lost('lost', 'Perdu'),
  found('found', 'Trouvé');

  const ReportKind(this.value, this.label);
  final String value;
  final String label;

  static ReportKind fromValue(String value) =>
      ReportKind.values.firstWhere((kind) => kind.value == value);
}

enum ReportCircumstance {
  lost('lost', 'Égaré'),
  stolen('stolen', 'Volé');

  const ReportCircumstance(this.value, this.label);
  final String value;
  final String label;

  static ReportCircumstance? fromValue(String? value) {
    if (value == null) return null;
    return ReportCircumstance.values
        .firstWhere((item) => item.value == value, orElse: () => ReportCircumstance.lost);
  }
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

/// Un document porté par un signalement. Le numéro n'est jamais renvoyé
/// par l'API, seule sa présence est connue.
class ReportDocument {
  const ReportDocument({
    required this.id,
    required this.documentType,
    required this.hasDocumentNumber,
  });

  final String id;
  final DocumentType documentType;
  final bool hasDocumentNumber;

  factory ReportDocument.fromJson(Map<String, dynamic> json) {
    return ReportDocument(
      id: json['id'] as String,
      documentType: DocumentType.fromValue(json['document_type'] as String),
      hasDocumentNumber: json['has_document_number'] as bool? ?? false,
    );
  }
}

/// Un document à déclarer, avant envoi. Le numéro part vers l'API puis
/// n'est plus conservé par l'application.
class DocumentDraft {
  DocumentDraft({required this.documentType, this.documentNumber = ''});

  DocumentType documentType;
  String documentNumber;

  Map<String, dynamic> toJson() => {
        'document_type': documentType.value,
        if (documentNumber.trim().isNotEmpty)
          'document_number': documentNumber.trim(),
      };
}

class Report {
  const Report({
    required this.id,
    required this.kind,
    required this.documents,
    required this.region,
    required this.status,
    required this.createdAt,
    this.circumstance,
    this.ownerNameMasked,
    this.commune,
    this.occurredOn,
    this.verificationQuestion,
    this.placeDetail,
    this.isPublished,
    this.latitude,
    this.longitude,
  });

  final String id;
  final ReportKind kind;
  final List<ReportDocument> documents;
  final String region;
  final ReportStatus status;
  final DateTime createdAt;
  final ReportCircumstance? circumstance;
  final String? ownerNameMasked;
  final String? commune;
  final DateTime? occurredOn;

  /// Visible par tous : il faut pouvoir y répondre pour revendiquer.
  final String? verificationQuestion;

  /// Champs présents uniquement dans la vue du propriétaire
  final String? placeDetail;
  final bool? isPublished;
  final double? latitude;
  final double? longitude;

  bool get hasVerificationQuestion =>
      verificationQuestion != null && verificationQuestion!.isNotEmpty;

  bool get hasAnyDocumentNumber =>
      documents.any((document) => document.hasDocumentNumber);

  DocumentType get mainDocumentType =>
      documents.isEmpty ? DocumentType.autre : documents.first.documentType;

  /// "Carte d'identité" ou "Carte d'identité +2" selon le nombre de pièces
  String get documentsLabel {
    if (documents.isEmpty) return 'Document';
    if (documents.length == 1) return documents.first.documentType.label;
    return '${documents.first.documentType.label} +${documents.length - 1}';
  }

    /// Le sens de la demande dépend du signalement : sur un document trouvé,
  /// le demandeur est le propriétaire ; sur un document perdu, c'est celui
  /// qui a récupéré la pièce.
  bool get isFound => kind == ReportKind.found;

  String get claimPrompt =>
      isFound ? 'Ce document est le vôtre ?' : 'Vous avez ce document ?';

  String get claimExplanation => isFound
      ? 'Répondez à la question du déclarant. Une bonne réponse vous donne '
        'son contact immédiatement.'
      : 'Dites au déclarant que vous avez son document. Une bonne réponse à '
        'sa question vous met en relation immédiatement.';

  String get claimAction =>
      isFound ? 'Envoyer ma demande' : "Signaler que je l'ai";

  /// Libellé du sens, enrichi de la circonstance quand elle est connue
  String get kindLabel =>
      circumstance == null ? kind.label : circumstance!.label;

  String get locationLabel =>
      commune == null || commune!.isEmpty ? region : '$commune, $region';

  factory Report.fromJson(Map<String, dynamic> json) {
    return Report(
      id: json['id'] as String,
      kind: ReportKind.fromValue(json['kind'] as String),
      documents: ((json['documents'] as List<dynamic>?) ?? [])
          .map((item) => ReportDocument.fromJson(item as Map<String, dynamic>))
          .toList(),
      region: json['region'] as String,
      status: ReportStatus.fromValue(json['status'] as String),
      createdAt: DateTime.parse(json['created_at'] as String),
      circumstance: ReportCircumstance.fromValue(json['circumstance'] as String?),
      ownerNameMasked: json['owner_name_masked'] as String?,
      commune: json['commune'] as String?,
      occurredOn: json['occurred_on'] == null
          ? null
          : DateTime.parse(json['occurred_on'] as String),
      verificationQuestion: json['verification_question'] as String?,
      placeDetail: json['place_detail'] as String?,
      isPublished: json['is_published'] as bool?,
      latitude: (json['latitude'] as num?)?.toDouble(),
      longitude: (json['longitude'] as num?)?.toDouble(),
    );
  }
}